from decimal import Decimal, ROUND_DOWN

import numpy as np
import cv2


class ImageRotater:
    def __init__(self, number_to_take_from_list=10, min_length_decrease_value=50, threshold_decrease_value=50,
                 max_gap=30):
        """
        画像から直線が検出されたときに画像を回転させるクラス

        Args:
            number_to_take_from_list: 角度リストから回転に使うものを取得する際に一部の角度だけ参照するがその際に参照する数
            min_length_decrease_value: 二値化画像から直線を検出出来なかった時に減らす、直線検出時の最小直線距離の数値
            threshold_decrease_value:  二値化画像から直線を検出出来なかった時に減らす、直線検出時の閾値の数値
            max_gap: 線同士が離れていても同一の直線だと判断する最大値
        """
        self._number_to_take_from_list = number_to_take_from_list
        self._min_length_decrease_value = min_length_decrease_value
        self._threshold_decrease_value = threshold_decrease_value
        self._max_gap = max_gap

        self.line = LineGetter()

    def get_result_deg(self, deg_list, img_canny, min_length, threshold):
        """
        角度のリストから条件に合う角度を取得

        Args:
            deg_list(list[float]): 角度のリスト
            img_canny(img_th): エッジ検出した二値化画像　
            min_length(int): 直線検出するときの最小直線距離
            threshold(int): 直線検出するときの閾値

        Returns:
            float: 画像回転時に使う角度
        """
        result_deg = None
        for deg in deg_list[:self._number_to_take_from_list]:
            img_canny_rot = self.rotation(img_canny, deg)
            horizontal_lines, _, _ = self.line.detect_line(img_canny_rot, min_length, threshold)
            horizontal_deg_list = [self._round_angle(horizontal_line) for horizontal_line in horizontal_lines
                                   if horizontal_lines is not None]
            # 正しく回転している場合は-0.5°~0.5°の角度以外は検出されない(?)
            if horizontal_deg_list and np.all(np.abs(horizontal_deg_list) <= 0.5):
                result_deg = deg
                break
        if result_deg is None:
            result_deg = self._get_median(deg_list)
        return result_deg

    @staticmethod
    def rotation(img, deg):
        """
        画像の回転

        Args:
            img(img_bgr): オリジナル画像を射影変換したもの
            deg(float): 画像回転時の角度

        Returns:
            img_bgr: 回転後の画像
        """
        rad = np.deg2rad(deg)
        h, w = img.shape[:2]
        # 回転後の画像サイズを計算
        w_rot = int(np.round(h * np.absolute(np.sin(rad)) + w * np.absolute(np.cos(rad))))
        h_rot = int(np.round(h * np.absolute(np.cos(rad)) + w * np.absolute(np.sin(rad))))
        # 回転
        rotation_matrix = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1)
        # 平行移動(rotation + translation)
        rotation_matrix[0][2] += (w_rot / 2 - w / 2)
        rotation_matrix[1][2] += (h_rot / 2 - h / 2)
        return cv2.warpAffine(img, rotation_matrix, (w_rot, h_rot), flags=cv2.INTER_CUBIC)

    @staticmethod
    def degree(x1, y1, x2, y2):
        """長辺が水平になるように、回転角を決める"""
        a, b = np.array([x1, y1]), np.array([x2, y2])
        vec = b - a
        rad = np.arctan2(vec[0], vec[1])
        deg = np.rad2deg(rad)

        # これがないと長辺を水平にするための角度範囲が-45～-135(or45~135)になる、numpyのときにも-90~90の角度でできるようにする
        deg = deg + 90
        if deg > 180:
            deg -= 360
        if 0 < np.abs(deg) < 180:
            deg = -deg

        if 90 < deg:
            deg -= 180
        if deg < -90:
            deg += 180

        if deg < -45:
            deg += 90
        if deg > 45:
            deg -= 90
        return deg

    def _round_angle(self, line):
        """小数点第2位を丸めた角度リストを作成"""
        x1, y1, x2, y2 = line[0]
        deg = self.degree(x1, y1, x2, y2)
        deg_decimal = Decimal(deg).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
        deg = float(deg_decimal)
        return deg

    @staticmethod
    def _get_median(deg_list):
        """角度リストの中央値取得"""
        deg_abs_list = np.abs(deg_list)
        deg_abs_min = np.min(deg_abs_list)
        condition = deg_abs_list - deg_abs_min < 30  # 角度の絶対値の最小より30以上離れている角度は削除
        new_deg_list = np.array(deg_list)[condition]
        return np.median(new_deg_list)


class LineGetter:
    def __init__(self, min_length_decrease_value=50, threshold_decrease_value=50, max_gap=30):
        """
        画像から直線が検出されたときに画像を回転させるクラス

        Args:
            min_length_decrease_value: 二値化画像から直線を検出出来なかった時に減らす、直線検出時の最小直線距離の数値
            threshold_decrease_value:  二値化画像から直線を検出出来なかった時に減らす、直線検出時の閾値の数値
            max_gap: 線同士が離れていても同一の直線だと判断する最大値
        """
        self._min_length_decrease_value = min_length_decrease_value
        self._threshold_decrease_value = threshold_decrease_value
        self._max_gap = max_gap

    def detect_line(self, img_th, min_length, threshold):
        """
        二値化画像から直線を検出

        Args:
            img_th (img_th): 製品の輪郭を表示した二値化画像
            min_length (int): 直線検出するときの最小直線距離
            threshold (int): 直線検出するときの閾値

        Returns:
            list(np.ndarray(X, 1, 4),) or None, int, int: 直線のリスト(右x, 右y, 左x, 左y) or None, 直線検出時の最小直線距離, 直線検出時の閾値
        """
        lines = None
        while min_length > 0:
            while threshold > 0:
                lines = cv2.HoughLinesP(img_th, 1, np.pi / 720,  # 角度は0.25°ずつ検出
                                        threshold=threshold, minLineLength=min_length, maxLineGap=self._max_gap)
                if lines is not None:
                    return lines, min_length, threshold
                else:
                    threshold -= self._threshold_decrease_value
            if lines is None:
                min_length -= self._min_length_decrease_value
        return None, min_length, threshold


if __name__ == '__main__':
    from preprocessing import Preprocess
    from perspective_transform import PerspectiveTransformer, LoadPerspectiveNumFile

    threshold_ = 500
    min_length_ = 500

    path_ = r""
    n = np.fromfile(path_, dtype=np.uint8)
    img_orig_ = cv2.imdecode(n, cv2.IMREAD_COLOR)
    height_, width_ = img_orig_.shape[:2]

    pre = Preprocess(width_, height_)
    load = LoadPerspectiveNumFile()
    line_ = LineGetter()
    rot = ImageRotater()
    pers = PerspectiveTransformer(width_, height_, load.pts)

    img_th_ = pre._detect_edge_from_original_img(img_orig_)
    lines_, min_length_, threshold_ = line_.detect_line(img_th_, min_length_, threshold_)
    if lines_ is None:  # 画像に製品が無い等で直線が検出されないとき
        img_trans_rot = img_orig_

    deg_list_ = pre._list_of_degree(lines_)
    result_deg_ = rot.get_result_deg(deg_list_, img_th_, min_length_, threshold_)
    img_trans_ = pers.transform(img_orig_)
    img_trans_rot_ = rot.rotation(img_trans_, result_deg_)

    cv2.namedWindow("img_trans_rot_", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("img_trans_rot_", 1200, 900)
    cv2.imshow("img_trans_rot_", img_trans_rot_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
