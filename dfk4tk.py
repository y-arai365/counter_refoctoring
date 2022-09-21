"""
アルゴ社のカメラDFK33UX183用のVideoCapture。
別途カメラ用のドライバーをインストールする必要あり。

set_exp_and_get_imageで露出を引数に明るさを変えて撮影した画像が得られる。
get_hdrで2枚の画像からHDR画像を作成。
使用レンズは松電社25mmレンズSM2520-MP20
"""

from cv2 import VideoCapture
import cv2
import numpy as np
import pickle

from load_config import load_config
from tisgrabber import TIS_CAM


config_file_path = "camera_config.xml"


class VideoCapture4DFK(VideoCapture):
    def __init__(self, d=0, w=3856, h=2764):
        """
        cv2.VideoCaptureを継承し、DFK33UJ003用に初期設定

        :param d: デバイス番号。基本0。PCによっては何故か1
        :param w: 横幅
        :param h: 高さ
        """
        self.d = d
        self.w = w
        self.h = h

        # tisgrabberで設定読込
        cam = TIS_CAM()
        devices = cam.GetDevices()
        if devices:
            device = devices[0].decode()
            cam.open(device)
            load_config(cam, config_file_path)

        # カメラのデバイス番号は基本0 但し、PCによって1になる場合がある
        super(VideoCapture4DFK, self).__init__(self.d)  # デバイス番号0
        if self.isOpened() is False:  # カメラと接続できなかった場合
            self.d = 1
            super(VideoCapture4DFK, self).__init__(self.d)  # デバイス番号1

        self.set(3, self.w)  # 幅
        self.set(4, self.h)  # 高さ
        self.set(6, cv2.VideoWriter_fourcc(*"YUY2"))  # ピクセルフォーマットをYUV 4:2:2に。

        self.exp = self.get(cv2.CAP_PROP_EXPOSURE)

    def get_frame_for_tk(self, first_width, first_height, ratio):
        """
        呼び出されるとカメラから一枚画像を読み込む。cap.read()。
        tkinter用に色変換。BGR　->　RGB
        :return: numpy配列のRGB画像
        """
        try:
            ret, frame = self.read()
            binary = pickle.dumps(frame)
            pickle_copy = pickle.loads(binary)
            pickle_copy = cv2.resize(pickle_copy, (int(first_width * ratio), int(first_height * ratio)))
            return pickle_copy, frame
        except cv2.error:
            self.__del__()
            blank = np.zeros((int(first_height * ratio), int(first_width * ratio), 3), np.uint8)
            return blank, blank

    def __del__(self):
        """
        カメラデバイス解放
        """
        # 呼び出し先でcap.release()が行われていない場合でもdel関数で解放する
        if self.isOpened() is True:
            self.release()

    def set_exp_and_get_image(self, exp):
        """
        設定した露光で画像撮影。
        パラメータ変更直後、すぐにはカメラに反映されないので、無駄にreadする必要がある。
        撮影後は元の露出設定に戻る。

        :param exp: 露出
        :return: 設定した露出で撮影した画像
        """
        self.set(15, exp)
        for i in range(3):
            self.read()
        _, img = self.read()
        self.set(15, self.exp)
        return img

    def get_hdr(self, img1, img2):
        """
        明暗を変えて撮った画像を合成しハイダイナミックレンジ画像を作成。
        入力できる画像の枚数は2枚に限定した。
        クラスにする必要ないかも。
        """
        img_list = [img1, img2]
        merge_mertens = cv2.createMergeMertens()
        res_mertens = merge_mertens.process(img_list)
        res_mertens_8bit = np.clip(res_mertens * 255, 0, 255).astype("uint8")
        return res_mertens_8bit


def main():
    cap = VideoCapture4DFK(1)  # デバイス番号は1。以降は通常のVideoCaptureと同様に扱えるはず。
    opened = cap.isOpened()
    cv2.namedWindow("img", cv2.WINDOW_NORMAL)
    cap.set(cv2.CAP_PROP_SETTINGS, 0)

    while True:
        ret, frame = cap.read()
        cv2.imshow("img", frame)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        elif k == ord("s"):
            cv2.imwrite("frame.jpg", frame)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
