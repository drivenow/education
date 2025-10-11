import easyocr
import os
import re
from datetime import datetime
from typing import List, Dict
# 初始化Reader（指定中文+英文，启用GPU）
reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
import cv2
import easyocr
import numpy as np
from sklearn.cluster import KMeans


class SmartDocumentOCR:
    def __init__(self):
        self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
        self.img_width = 0
        self.img_height = 0

    def analyze_layout(self, image_path):
        """ 智能文档布局分析 """
        # 读取图像并初始化参数
        img = cv2.imread(image_path)
        if img is None:
            import imageio
            tmp = imageio.mimread(image_path)
            if tmp is not None:
                tmp = np.array(tmp)
                img = tmp[0][:, :, :3]
            # raise FileNotFoundError(f"无法读取图像: {image_path}")

        self.img_height, self.img_width = img.shape[:2]
        results = self.reader.readtext(img, paragraph=False, detail=1)

        if not results:
            return None, None

        # 提取多维特征
        features, boxes = [], []
        for (bbox, text, conf) in results:
            y_min = min(p[1] for p in bbox)
            y_max = max(p[1] for p in bbox)
            x_center = np.mean([p[0] for p in bbox])
            height = y_max - y_min
            width = max(p[0] for p in bbox) - min(p[0] for p in bbox)

            # 特征加权组合
            features.append([
                y_min / self.img_height * 0.7,  # 垂直位置（主要）
                (height / self.img_height) * 3,  # 高度（3倍权重）
                (x_center / self.img_width) * 0.3,
                (len(text) / 50) * 0.2  # 文本长度
            ])
            boxes.append((bbox, text, conf))

        # 三级聚类分析
        kmeans = KMeans(n_clusters=3, random_state=42).fit(features)
        clusters = kmeans.labels_

        # 识别最佳标题簇
        cluster_scores = []
        for i in range(3):
            cluster_data = [f for f, c in zip(features, clusters) if c == i]
            avg_y = np.mean([d[0] for d in cluster_data])
            avg_height = np.mean([d[1] for d in cluster_data])
            score = (1 - avg_y) * 0.6 + avg_height * 0.4  # 位置+高度评分
            cluster_scores.append(score)

        title_cluster = np.argmax(cluster_scores)
        title_boxes = [boxes[i] for i, c in enumerate(clusters) if c == title_cluster]

        # 验证标题区域有效性
        if self._validate_title(title_boxes):
            y_min = max(0, int(min(p[1] for b, _, _ in title_boxes for p in b)) - 20)
            y_max = min(self.img_height, int(max(p[1] for b, _, _ in title_boxes for p in b)) + 20)
            y_max = min(y_max, int(self.img_height * 0.6))  # 标题最多占60%高度
            return (y_min, y_max), title_boxes
        return None, None

    def _validate_title(self, title_boxes):
        """ 标题区域验证 """
        if not title_boxes or len(title_boxes) > 10:
            return False

        # 计算平均字体高度
        avg_height = np.mean([max(p[1] for p in bbox) - min(p[1] for p in bbox)
                              for (bbox, _, _) in title_boxes])
        return avg_height > (self.img_height / 35)  # 大于正文字体1.5倍

    def _detect_columns(self, img):
        """ 左右均分分栏检测算法 """
        # 步骤1：检测并裁剪边栏空白区域
        cropped_img, x_start, x_end = self._crop_margins(img)

        # 步骤2：计算有效区域的中间位置
        split_x = x_start + (x_end - x_start) // 2

        # 有效性验证：确保分栏位置在有效区域内
        min_valid_width = self.img_width * 0.3  # 最小有效分栏宽度
        if (x_end - x_start) > min_valid_width:
            return True, split_x
        return False, 0

    def _process_columns(self, img):
        """ 改进分栏内容处理 """
        has_columns, split_x = self._detect_columns(img)
        has_columns = False
        if not has_columns:
            return self.reader.readtext(img, detail=0, paragraph=True)

        # 强制分栏处理（即使一侧无内容）
        left_img = img[:, :split_x]
        right_img = img[:, split_x:]

        # 双线程识别优化
        from threading import Thread
        results = [None, None]

        def read_left():
            results[0] = self.reader.readtext(left_img, detail=0, paragraph=True)

        def read_right():
            results[1] = self.reader.readtext(right_img, detail=0, paragraph=True)

        t1 = Thread(target=read_left)
        t2 = Thread(target=read_right)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        return results[0] + results[1]

    def _crop_margins(self, img, margin_threshold=0.15):
        """ 智能裁剪边栏空白 """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # 水平投影分析
        horizontal_proj = np.sum(edges, axis=0)

        # 动态检测左右边界
        x_start = self._find_content_start(horizontal_proj, img.shape[1], margin_threshold)
        x_end = self._find_content_end(horizontal_proj, img.shape[1], margin_threshold)

        # 裁剪边栏
        return img[:, x_start:x_end], x_start, x_end

    def _find_content_start(self, proj, total_width, threshold_ratio):
        """ 找到正文左边界 """
        threshold = np.max(proj) * 0.1
        margin = int(total_width * threshold_ratio)

        # 从左侧开始扫描
        for x in range(margin, total_width - margin):
            if proj[x] > threshold:
                return max(0, x - 20)  # 保留少量边界
        return 0

    def _find_content_end(self, proj, total_width, threshold_ratio):
        """ 找到正文右边界 """
        threshold = np.max(proj) * 0.1
        margin = int(total_width * threshold_ratio)

        # 从右侧开始扫描
        for x in range(total_width - margin, margin, -1):
            if proj[x] > threshold:
                return min(total_width, x + 20)
        return total_width

    def _find_column_gap(self, smoothed_proj, width):
        """ 在裁剪后的区域内寻找分栏间隙 """
        avg_density = np.mean(smoothed_proj)
        gap_threshold = avg_density * 0.3
        max_gap, best_x, current_start = 0, 0, -1

        for x in range(1, len(smoothed_proj) - 1):
            if smoothed_proj[x - 1] < gap_threshold and smoothed_proj[x] < gap_threshold and smoothed_proj[
                x + 1] < gap_threshold:
                if current_start == -1:
                    current_start = x
                current_gap = x - current_start
                if current_gap > max_gap:
                    max_gap = current_gap
                    best_x = current_start + current_gap // 2
            else:
                current_start = -1

        return best_x, max_gap

    def _postprocess_content(self, raw_content, metadata_title):
        """ 后处理过滤标题和作者信息 """
        filtered = []
        title_keywords = ["作者", "插画", "|"]

        for paragraph in raw_content:
            # 过滤条件1：包含作者/插画关键词
            if any(kw in paragraph for kw in title_keywords):
                # 验证是否为有效作者信息（包含分隔符）
                if "|" in paragraph and any(kw in paragraph for kw in ["作者", "插画"]):
                    continue

            # 过滤条件2：与元数据标题高度相似
            if metadata_title and self._similarity(paragraph, metadata_title) > 0.7:
                continue

            # 过滤条件3：短文本且包含标题特征
            if len(paragraph) < 30 and any(c.isdigit() for c in paragraph):
                if self._is_title_pattern(paragraph):
                    continue

            filtered.append(paragraph)
        return filtered

    def _similarity(self, s1, s2):
        """ 文本相似度计算 """
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1, s2).ratio()

    def _is_title_pattern(self, text):
        """ 检测标题特征模式 """
        # 匹配数字编号模式（如：熘兔 8g酮箩 1作者）
        if re.search(r'\d+作者|\d+插画', text):
            return True
        # 匹配特殊分隔符组合
        if re.search(r'[\d\W]{3,}', text):  # 包含3个及以上数字/特殊字符
            return True
        return False

    def parse_document(self, image_path, title_recongnize=False):
        """ 修改后的解析流程 """
        title_zone, title_boxes = self.analyze_layout(image_path)
        img = cv2.imread(image_path)
        if img is None:
            import imageio
            tmp = imageio.mimread(image_path)
            if tmp is not None:
                tmp = np.array(tmp)
                img = tmp[0][:, :, :3]

        # 提取元数据
        metadata = {}
        if title_boxes and title_recongnize:
            sorted_boxes = sorted(title_boxes, key=lambda x: min(p[1] for p in x[0]))
            metadata["title"] = " ".join([t for _, t, _ in sorted_boxes if len(t) < 30])

        # 处理正文区域
        body_img = img[title_zone[1] + 10:] if title_zone and title_recongnize else img
        raw_content = self._process_columns(body_img) if body_img.size > 0 else []

        # 后处理过滤
        processed_content = self._postprocess_content(
            raw_content,
            metadata.get("title", "")
        )

        return {
            "metadata": metadata,
            "content": "\n".join(processed_content) if processed_content else "未识别到正文内容"
        }


class ArticleProcessor:
    def __init__(self, base_dir: str, ocr:SmartDocumentOCR, output_path:str='processed'):
        self.base_dir = base_dir
        self.ocr = ocr
        self.current_article: Dict = None
        self.article_counter = 1
        self.article_files = []
        self.output_path = output_path


    def process_image_series(self):
        """处理整个图片序列的主流程"""
        # 获取并按时间排序图片
        sorted_images = self._get_sorted_images()

        for img_path in sorted_images:
            print(f"正在处理: {os.path.basename(img_path)}")

            # OCR解析
            result = self.ocr.parse_document(img_path)

            # 判断是否新文章
            if 0<str(result['metadata']).find("作者") < 50 or result['metadata'] or 0<str(result['content']).find("作者") < 50:
                self._save_current_article()
                self._init_new_article(result['metadata'])

            # 追加内容
            if result['content']:
                if not self.current_article:
                    self._init_new_article(result['metadata'])
                self.current_article['content'].append(result['content'])

        # 保存最后一篇文章
        self._save_current_article()
        return self.article_files

    def _get_sorted_images(self) -> List[str]:
        """获取按时间排序的图片列表"""
        images = []
        for fname in os.listdir(self.base_dir):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                # os获取文件的时间
                timestamp = os.path.getmtime(os.path.join(self.base_dir, fname))
                images.append((timestamp, os.path.join(self.base_dir, fname)))
        # 按时间排序
        return [img[1] for img in sorted(images, key=lambda x: x[0])]


    def _init_new_article(self, metadata: Dict):
        """初始化新文章"""
        self.current_article = {
            'metadata': metadata,
            'content': [],
            'start_time': datetime.now().strftime("%Y%m%d_%H%M%S")
        }

    def _save_current_article(self):
        """保存当前文章"""
        if not self.current_article or not self.current_article['content']:
            return

        # 生成安全文件名
        title = self.current_article['metadata'].get('title', f'未命名文章_{self.article_counter}')
        clean_title = re.sub(r'[\\/*?:"<>|]', '', title)[:50]

        filename = f"{self.article_counter:03d}_{clean_title}.txt"
        filepath = os.path.join(self.base_dir, self.output_path, filename)

        # 确保输出目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # 合并内容并保存
        full_content = '\n\n'.join(self.current_article['content'])
        full_content = re.sub(r'\d*\n', '', full_content)
        full_content = full_content.replace(' ', '').replace('\n', '')
        full_content = full_content.replace('。', '。\n')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)

        print(f"已保存文章: {filename}")
        self.article_counter += 1
        self.article_files.append(filepath)



# 使用示例
if __name__ == "__main__":
    import sys

    # if len(sys.argv) < 2:
    #     print("请拖放图片文件到本程序")
    #     sys.exit()

    base_dir = r"D:\story_pictures\kehuanshijie"
    base_dir = r"D:\story_pictures\1"
    img_path = os.path.join(base_dir, "6.jpg")

    ocr = SmartDocumentOCR()
    result = ocr.parse_document(img_path)

    print("\n=== 文档解析结果 ===")
    print(f"[标题] {result['metadata'].get('title', '无标题')}")
    print(f"\n[正文内容]\n{result['content']}")

    processor = ArticleProcessor(base_dir, ocr)
    processor.process_image_series()
