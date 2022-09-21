from decimal import Decimal, ROUND_DOWN, ROUND_UP
import math

import cv2
import numpy as np
from PIL import Image

from _perspective_transform import PerspectiveTransformer


pers_num_path = "pers_num.npy"
pts = np.load(pers_num_path)[0]


class Preprocess:
    def __init__(self, width, height):
        """
        画像を射影変換、画像内の製品が水平になるように回転するクラス

        Args:
            width (int): オリジナル画像の幅
            height (int): オリジナル画像の高さ
        """
        self.perspective = PerspectiveTransformer(width, height, pts)
        self.kernel = np.ones((3, 3), np.uint8)
        self.max_gap = 30

    def preprocessing(self, img, first_min_length, first_threshold):
        """
        画像を射影変換、画像内の製品が水平になるように回転する
        Args:
            img (img_bgr): オリジナル画像
            first_min_length (int): 二値化画像から直線をハフ検出するときの初めの最小直線距離
            first_threshold (int): 二値化画像から直線をハフ検出するときの初めの閾値

        Returns:
            img_bgr: 射影変換・回転後の画像
        """
        img_canny = self._image_pre_process(img)
        try:
            # 直線を検出、そのときの閾値・最小直線距離を取得
            lines, min_length, threshold = self._detect_line(img_canny, first_min_length, first_threshold)
            if lines is None:
                img_trans_rot = img
                return img_trans_rot
                # print("break")
                # exit()
            deg_list = self._list_of_degree(lines)

            result_deg = self._get_result_deg(deg_list, img_canny, min_length, threshold)
            img_trans = self.perspective.transform(img)
            img_trans_rot = self._rotation(img_trans, result_deg)
            # return img_trans_rot

        except Exception as err:
            import traceback
            import datetime
            import os
            error_dir = "./preprocessing_error/"
            os.makedirs(error_dir, exist_ok=True)
            now = datetime.datetime.now()
            str_now = "{0:%m%d_%H%M}".format(now)
            file_name = error_dir + str_now + ".txt"
            with open(file_name, "w") as f:
                pass
            traceback.print_exc(file=open(file_name, "a"))
            img_trans_rot = img
        finally:
            result = img_trans_rot
        return result

    def _image_pre_process(self, image):
        """
        直線検出前の事前処理
        Args:
            image (img_bgr): オリジナル画像

        Returns:
            img_th: 製品の輪郭を表示した二値化画像
        """
        # 画像を2値化してエッジ検出する
        img_gray = self._gray_scale(image)
        img_canny = self._canny_edge_detect(img_gray)  # エッジ検出
        img_pers = self.perspective.transform(img_canny)  # 射影変換
        img_close = self._morphology_close(img_pers)
        # エッジの穴の部分を埋めるための輪郭検出
        img_close = self._draw_contours(img_close)
        # 製品部分ではなく余白部分を抽出
        img_canny_inv = self._invert(img_close)
        img_canny_inv = self._erode(img_canny_inv)
        # 余白のエッジを抽出
        return self._canny_edge_detect(img_canny_inv)

    def _detect_line(self, img_th, _min_length, _threshold):
        """
        二値化画像から直線を検出

        Args:
            img_th (img_th): 製品の輪郭を表示した二値化画像
            _min_length (int): 直線検出するときの最小直線距離
            _threshold (int): 直線検出するときの閾値

        Returns:
            list(np.ndarray(X, 1, 4),) or None, int, int: 直線のリスト(右x, 右y, 左x, 左y) or None, 直線検出時の最小直線距離, 直線検出時の閾値
        """
        lines = None
        min_length = _min_length
        while min_length > 0:
            threshold = _threshold
            while threshold > 0:
                lines = cv2.HoughLinesP(img_th, 1, np.pi / 720,  # 角度は0.5°ずつ検出
                                        threshold=threshold, minLineLength=min_length, maxLineGap=self.max_gap)
                if lines is not None:
                    return lines, min_length, threshold
                else:
                    threshold -= 50
            if lines is None:
                min_length -= 50
        return None, min_length, threshold

    def _list_of_degree(self, lines):
        """linesを基にして、傾いている角度のリスト取得"""
        deg_list = []
        deg_list_2 = []
        for line in lines:  # 直線がない・足りない場合
            x1, y1, x2, y2 = line[0]
            deg = self._degree(x1, y1, x2, y2)  # 角度を求める
            if deg not in deg_list:  # 角度がかぶっている場合はスルー
                deg_list.append(deg)
                deg_list_2.append(deg)
            else:
                deg_list_2.append(deg)
        return deg_list

    def _get_result_deg(self, deg_list, img_canny, min_length, threshold):
        """角度のリストから条件に合う角度を取得"""
        result_deg = None
        for deg in deg_list[:10]:
            img_canny_rot = self._rotation(img_canny, deg)
            horizontal_lines, _, _ = self._detect_line(img_canny_rot, min_length, threshold)
            if horizontal_lines is not None:  # 直線が検出できた場合
                horizontal_deg_list = []
                for horizontal_line in horizontal_lines:
                    horizontal_deg_list = self._list_of_rounded_angles(horizontal_line, horizontal_deg_list)
                # 正しく回転している場合は-0.5~0.5の角度以外は検出されない(?)
                if len(horizontal_deg_list) > 0 and np.all(np.array(horizontal_deg_list) <= 0.5) \
                        and np.all(np.array(horizontal_deg_list) >= -0.5):
                    result_deg = deg
                    break
        if result_deg is None:
            result_deg = self._get_median(deg_list)
        return result_deg

    @staticmethod
    def _rotation(img, deg):
        """画像の回転"""
        img_pil = Image.fromarray(img)
        img_rot = img_pil.rotate(deg, resample=Image.BILINEAR, expand=True)
        return np.asarray(img_rot)

    @staticmethod
    def _gray_scale(img):
        """グレースケール"""
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def _canny_edge_detect(img):
        """キャニー検出"""
        return cv2.Canny(img, 100, 200)

    def _morphology_close(self, img_th):
        """クロージング処理"""
        return cv2.morphologyEx(img_th, cv2.MORPH_CLOSE, self.kernel)

    @staticmethod
    def _draw_contours(img_th):
        """エッジの穴埋め"""
        img_th_copy = img_th.copy()
        contours, hierarchy = cv2.findContours(img_th_copy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭検出
        for cnt in contours:
            cv2.drawContours(img_th_copy, [cnt], -1, 255, -1)
        return img_th_copy

    @staticmethod
    def _invert(img_th):
        """ネガポジ変換"""
        return cv2.bitwise_not(img_th)

    def _erode(self, img_th):
        """エロード処理"""
        return cv2.erode(img_th, self.kernel, iterations=1)

    @staticmethod
    def _degree(x1, y1, x2, y2):
        """長辺が水平になるように、回転角を決める"""
        rad = math.atan2(y1 - y2, x1 - x2)
        deg = math.degrees(rad)
        if 90 < deg:
            deg -= 180
        if deg < -90:
            deg += 180

        if deg < -45:
            deg += 90
        if deg > 45:
            deg -= 90
        return deg

    def _list_of_rounded_angles(self, line, deg_list):
        """小数点第2位を丸めた角度リストを作成"""
        x1, y1, x2, y2 = line[0]
        _deg = self._degree(x1, y1, x2, y2)
        if _deg < 0:
            _deg_decimal = Decimal(str(_deg)).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
            _deg = float(_deg_decimal)
        else:
            _deg_decimal = Decimal(str(_deg)).quantize(Decimal("0.1"), rounding=ROUND_UP)
            _deg = float(_deg_decimal)
        if _deg != -45.0 and _deg != 45.0:
            if _deg not in deg_list:
                deg_list.append(_deg)
        return deg_list

    @staticmethod
    def _get_median(deg_list):
        """角度リストの中央値取得"""
        deg_abs_list = []
        for _deg in deg_list:
            deg_abs_list.append(abs(_deg))
        # 45°付近の直線が検出されたが他の角度の直線が検出されている場合、誤りであることが多いので削除
        while True:
            # 角度の絶対値の最小と最大の差が10以上ある場合は最大を削除
            deg_min = np.min(deg_abs_list)
            deg_max = np.max(deg_abs_list)
            if deg_max - deg_min > 30:
                _deg_list = []
                _deg_abs_list = []
                for deg in deg_list:  # 最大の角度がいくつか存在する可能性があるので新しいリストを作成
                    if abs(deg) != deg_max:
                        _deg_list.append(deg)
                for deg in deg_abs_list:
                    if deg != deg_max:
                        _deg_abs_list.append(deg)
                deg_list = _deg_list
                deg_abs_list = _deg_abs_list
            else:
                break
        return np.median(deg_list)


if __name__ == '__main__':
    import time

    # path = r"count/result/20220407/1200-1600-2/2173/上9/exp-4.jpg"
    path = r"count/result/20220407/1153-00113/4002/上7-49/exp-4.jpg"
    # path = r"\\192.168.11.6\develop-data\撮影データ\個数カウントv2.3.0\180-832\下19\frame.jpg"

    pers_num_path = "pers_num.npy"
    pts = np.load(pers_num_path)[0]

    threshold_ = 500
    min_length_ = 500
    max_gap_ = 30

    n = np.fromfile(path, dtype=np.uint8)
    img_ = cv2.imdecode(n, cv2.IMREAD_COLOR)
    _height, _width = img_.shape[:2]

    # img_th_ = np.zeros((_width, _height), dtype=np.uint8)
    # img_ = cv2.cvtColor(img_th_, cv2.COLOR_GRAY2BGR)

    pre = Preprocess(_width, _height)
    pers = PerspectiveTransformer(_width, _height, pts)

    start = time.time()
    img_trans_rot_ = pre.preprocessing(img_, min_length_, threshold_)
    stop = time.time()
    print(stop-start)

    cv2.namedWindow("i2", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("i2", 1200, 900)
    cv2.imshow("i2", img_trans_rot_)
    cv2.namedWindow("i3", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("i3", 1200, 900)
    cv2.imshow("i3", img_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
