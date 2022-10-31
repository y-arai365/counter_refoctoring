from decimal import Decimal, ROUND_DOWN

import cv2
import numpy as np

from perspective_transform import PerspectiveTransformer

# TODO: パスをモジュールに直接書かない。というか、多分今後ptsを読み込むクラスを作ると思う。
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
        self._kernel = np.ones((3, 3), np.uint8)  # TODO: マジックナンバー。ハードコーディングしない。
        self._max_gap = 30  # TODO: マジックナンバー。ハードコーディングしない。
        self._error_dir = "./preprocessing_error/"
        self._threshold_decrease_value = 50
        self._min_length_decrease_value = 50
        self._number_to_take_from_list = 10
        self._canny_threshold_1 = 100
        self._canny_threshold_2 = 200

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
        img_canny = self._img_pre_process(img)
        # 直線を検出、そのときの閾値・最小直線距離を取得
        lines, min_length, threshold = self._detect_line(img_canny, first_min_length, first_threshold)
        if lines is None:  # 画像に製品が無い等で直線が検出されないとき
            img_trans_rot = img
            return img_trans_rot
        deg_list = self._list_of_degree(lines)
        result_deg = self._get_result_deg(deg_list, img_canny, min_length, threshold)
        img_trans = self.perspective.transform(img)
        img_trans_rot = self._rotation(img_trans, result_deg)
        return img_trans_rot

    def _img_pre_process(self, img):
        """
        直線検出前の事前処理
        Args:
            img (img_bgr): オリジナル画像

        Returns:
            img_th: 製品の輪郭を表示した二値化画像
        """
        # 画像を2値化してエッジ検出する
        img_gray = self._gray_scale(img)
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

    def _detect_line(self, img_th, min_length, threshold):
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

    def _list_of_degree(self, lines):
        """linesを基にして、傾いている角度のリスト取得"""
        deg_list = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            deg = self._degree(x1, y1, x2, y2)  # 角度を求める
            deg_list.append(deg)
        return list(set(deg_list))

    def _get_result_deg(self, deg_list, img_canny, min_length, threshold):
        """角度のリストから条件に合う角度を取得"""
        result_deg = None
        for deg in deg_list[:self._number_to_take_from_list]:
            img_canny_rot = self._rotation(img_canny, deg)
            horizontal_lines, _, _ = self._detect_line(img_canny_rot, min_length, threshold)
            if horizontal_lines is not None:  # 直線が検出できた場合
                horizontal_deg_list = []
                for horizontal_line in horizontal_lines:
                    horizontal_deg_list = self._list_of_rounded_angles(horizontal_line, horizontal_deg_list)
                # 正しく回転している場合は-0.5°~0.5°の角度以外は検出されない(?)
                if len(horizontal_deg_list) and -0.5 <= np.all(np.array(horizontal_deg_list) <= 0.5):
                    result_deg = deg
                    break
        if result_deg is None:
            result_deg = self._get_median(deg_list)
        return result_deg

    @staticmethod
    def _rotation(img, deg):
        """画像の回転"""
        deg_rad = deg/180*np.pi
        h, w = img.shape[:2]
        # 回転後の画像サイズを計算
        w_rot = int(np.round(h * np.absolute(np.sin(deg_rad)) + w * np.absolute(np.cos(deg_rad))))
        h_rot = int(np.round(h * np.absolute(np.cos(deg_rad)) + w * np.absolute(np.sin(deg_rad))))
        # 回転
        rotation_matrix = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1)
        # 平行移動(rotation + translation)
        affine_matrix = rotation_matrix.copy()
        affine_matrix[0][2] = affine_matrix[0][2] - w / 2 + w_rot / 2
        affine_matrix[1][2] = affine_matrix[1][2] - h / 2 + h_rot / 2
        return cv2.warpAffine(img, affine_matrix, (w_rot, h_rot), flags=cv2.INTER_CUBIC)

    @staticmethod
    def _gray_scale(img):
        """グレースケール"""
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def _canny_edge_detect(self, img):
        """キャニー検出"""
        return cv2.Canny(img, self._canny_threshold_1, self._canny_threshold_2)

    def _morphology_close(self, img_th):
        """クロージング処理"""
        return cv2.morphologyEx(img_th, cv2.MORPH_CLOSE, self._kernel)

    @staticmethod
    def _draw_contours(img_th):
        """エッジの穴埋め"""
        img_th_copy = img_th.copy()
        contours, _ = cv2.findContours(img_th_copy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭検出
        cv2.drawContours(img_th_copy, contours, -1, 255, -1)
        return img_th_copy

    @staticmethod
    def _invert(img_th):
        """ネガポジ変換"""
        return cv2.bitwise_not(img_th)

    def _erode(self, img_th):
        """エロード処理"""
        return cv2.erode(img_th, self._kernel, iterations=1)

    @staticmethod
    def _degree(x1, y1, x2, y2):
        """長辺が水平になるように、回転角を決める"""
        a, b = np.array([x1, y1]), np.array([x2, y2])
        vec = b - a
        rad = np.arctan2(vec[0], vec[1])
        deg = np.rad2deg(rad)

        # これがないと長辺を水平にするための角度範囲が-45～-135(or45~135)になる、math.atan2のときの角度に合わせている
        deg = deg + 90
        if deg > 180:
            deg -= 360
        if 0 < deg < 180:
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

    def _list_of_rounded_angles(self, line, deg_list):
        """小数点第2位を丸めた角度リストを作成"""
        x1, y1, x2, y2 = line[0]
        deg = self._degree(x1, y1, x2, y2)
        deg_decimal = Decimal(deg).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
        deg = float(deg_decimal)
        deg_list.append(deg)
        if deg != -45.0 and deg != 45.0:
            if deg not in deg_list:
                deg_list.append(deg)
        return deg_list

    @staticmethod
    def _get_median(deg_list):
        """角度リストの中央値取得"""
        deg_abs_list = np.abs(deg_list)
        deg_abs_min = np.min(deg_abs_list)
        new_deg_list = []
        for index, boolean in enumerate((deg_abs_list - deg_abs_min) < 30):  # 角度の絶対値の最小より30以上離れている角度は削除
            if boolean:
                new_deg_list.append(deg_list[index])
        return np.median(new_deg_list)


if __name__ == '__main__':
    import time

    path = ""

    pers_num_path = "pers_num.npy"
    pts = np.load(pers_num_path)[0]

    threshold_ = 500
    min_length_ = 500
    max_gap_ = 30

    n = np.fromfile(path, dtype=np.uint8)
    img_ = cv2.imdecode(n, cv2.IMREAD_COLOR)
    height_, width_ = img_.shape[:2]

    pre = Preprocess(width_, height_)
    pers = PerspectiveTransformer(width_, height_, pts)

    start = time.time()
    img_trans_rot_ = pre.preprocessing(img_, min_length_, threshold_)
    stop = time.time()
    print(stop-start)

    cv2.namedWindow("img", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("img", 1200, 900)
    cv2.imshow("img", img_trans_rot_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
