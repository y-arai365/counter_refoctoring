import base64
from io import BytesIO

import qrcode


class QRCodeGenerator:
    def __init__(self):
        self._qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )

    def generate(self, data):
        """QRコードのpil画像を生成

        Args:
            data (str): QRコードに書き込む文字列。

        Returns:
            PiLImage: pillow画像。二値。

        """
        self._qr.clear()

        self._qr.add_data(data)
        self._qr.make(fit=True)

        img_pil = self._qr.make_image()
        return img_pil


class QRCodeBase64Generator(QRCodeGenerator):
    def __init__(self, image_format="png"):
        super().__init__()

        self._format = image_format

    def generate(self, data):
        """QRコード画像をBase64形式に変換した文字列を生成

        Args:
            data (str): QRコードに書き込む文字列。

        Returns:
            str: QRコードのpng画像をbase64に変換した文字列

        """
        img_pil = super().generate(data)
        return self._convert_to_base64(img_pil)

    def _convert_to_base64(self, img_pil):
        # メモリに画像をバイト列で保存
        buffer = BytesIO()
        img_pil.save(buffer, format=self._format)
        # バイト列をBase64に変換
        return base64.b64encode(buffer.getvalue()).decode("ascii")


if __name__ == '__main__':
    qr_gen = QRCodeBase64Generator()

    img_pil_ = qr_gen.generate("abcabcabcabcabcabcabcabcabcabcabcabcabcabcabcabc")
    print(img_pil_)

    img_pil_2 = qr_gen.generate("123")
    print(img_pil_2)
