import sys
import warnings
from logger import logger
warnings.filterwarnings("ignore")
import paddle
import torch
import time


device = "cuda:0" if torch.cuda.is_available() else "cpu"

def speech_recognition(asrclient_executor, filename):
    if not asrclient_executor:
        from paddlespeech.server.bin.paddlespeech_client import ASRClientExecutor
        asrclient_executor = ASRClientExecutor()
    if not text_executor:
        from paddlespeech.cli.text import TextExecutor
        text_executor = TextExecutor()

    # 访问服务端
    t1 = time.time()
    res = asrclient_executor(
        input=filename,
        server_ip="192.168.1.6",
        port=8090,
        sample_rate=16000,
        lang="zh_cn",
        audio_format="wav")
    # 识别标点
    text = text_executor(
        text=res,
        task='punc',
        model='ernie_linear_p7_wudao',
        lang='zh',
        config=None,
        ckpt_path=None,
        punc_vocab=None,
        device=paddle.get_device())
    logger.info('Text Result: {}. {}'.format(text, time.time() - t1))
    return text

def tmp():
    import paddle
    from paddlespeech.cli.asr.infer import ASRExecutor
    import paddle
    from paddlespeech.cli.st import STExecutor
    audio_file = "C:\\Users\\fullmetal\\Desktop\\乐乐\\苏杰学习材料\\新思维1AMp3音频\\新思维1AMp3音频\\NWTEG_PB1A_Ch1_A\\chunk4.wav"
    audio_file = "output_audio.wav"

    # 访问本地
    st_executor = STExecutor()#英文转中文
    # 尝试失败
    # text = st_executor(
    #     model='fat_st_ted',
    #     src_lang='en',
    #     tgt_lang='zh',
    #     sample_rate=16000,
    #     config=None,  # Set `config` and `ckpt_path` to None to use pretrained model.
    #     ckpt_path=None,
    #     audio_file=audio_file,
    #     device=paddle.get_device())
    # logger.info('ST Result: \n{}'.format(text))

    # asr = ASRExecutor()#语音转文本
    # result = asr(audio_file=audio_file, model="transformer_librispeech", lang="en", codeswitch = False)  # 录音文件地址
    # logger.info(result)

if __name__ == '__main__':
    filename = "C:\\Users\\fullmetal\\Desktop\\NWTEG_PB1A_Ch1_A.mp3"
    # speech_recognition(asrclient_executor, filename)
    from paddleocr import PaddleOCR, draw_ocr

    # Paddleocr supports Chinese, English, French, German, Korean and Japanese
    # You can set the parameter `lang` as `ch`, `en`, `french`, `german`, `korean`, `japan`
    # to switch the language model in order
    ocr = PaddleOCR(use_angle_cls=True, lang='en')  # need to run only once to download and load model into memory
    img_path = 'PaddleOCR/doc/imgs_en/img_12.jpg'
    result = ocr.ocr(img_path, cls=True)
    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            print(line)

    # draw result
    from PIL import Image

    result = result[0]
    image = Image.open(img_path).convert('RGB')
    boxes = [line[0] for line in result]
    txts = [line[1][0] for line in result]
    scores = [line[1][1] for line in result]
    im_show = draw_ocr(image, boxes, txts, scores, font_path='/path/to/PaddleOCR/doc/fonts/simfang.ttf')
    im_show = Image.fromarray(im_show)
    im_show.save('result.jpg')


