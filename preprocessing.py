import cv2
import numpy as np

from perspective_transform import PerspectiveTransformer, LoadPerspectiveNumFile
from rotation import ImageRotater, LineGetter


class Preprocess:
    def __init__(self, width, height, k_size=3, canny_threshold_1=100, canny_threshold_2=200):
        """
        画像を射影変換、画像内の製品が水平になるように回転するクラス

        Args:
            width (int): オリジナル画像の幅
            height (int): オリジナル画像の高さ
            k_size (int): クロージング、エロードに使うカーネル値
            canny_threshold_1 (int): canny法でエッジ検出するときに他のエッジと隣接するものか判断する閾値
            canny_threshold_2 (int): canny法でエッジ検出するときにエッジか否か判断する閾値
        """
        self._rotate = ImageRotater()
        self._line = LineGetter()
        self._perspective = PerspectiveTransformer(width, height, LoadPerspectiveNumFile().pts)

        self._kernel = np.ones((k_size, k_size), np.uint8)
        self._canny_threshold_1 = canny_threshold_1
        self._canny_threshold_2 = canny_threshold_2

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
        img_canny = self._detect_edge_from_original_img(img)
        # 直線を検出、そのときの閾値・最小直線距離を取得
        lines, min_length, threshold = self._line.detect_line(img_canny, first_min_length, first_threshold)
        if lines is None:  # 画像に製品が無い等で直線が検出されないとき
            img_trans_rot = img
            return img_trans_rot
        deg_list = self._list_of_degree(lines)
        result_deg = self._rotate.get_result_deg(deg_list, img_canny, min_length, threshold)
        img_trans = self._perspective.transform(img)
        img_trans_rot = self._rotate.rotation(img_trans, result_deg)
        return img_trans_rot

    def _list_of_degree(self, lines):
        """
        linesを基にして、傾いている角度のリスト取得

        Args:
            lines(list(np.ndarray(X, 1, 4),) or None): 直線のリスト(右x, 右y, 左x, 左y) or None

        Returns:
            list(float): 直線の座標をもとにした角度のリスト
        """
        deg_list_set = {self._rotate.degree(line[0][0], line[0][1], line[0][2], line[0][3]) for line in lines}
        return list(deg_list_set)

    def _detect_edge_from_original_img(self, img):
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
        img_pers = self._perspective.transform(img_canny)  # 射影変換
        img_close = self._morphology_close(img_pers)
        # エッジの穴の部分を埋めるための輪郭検出
        img_close = self._draw_contours(img_close)
        # 製品部分ではなく余白部分を抽出
        img_canny_inv = self._invert(img_close)
        img_canny_inv = self._erode(img_canny_inv)
        # 余白のエッジを抽出
        return self._canny_edge_detect(img_canny_inv)

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
        contours, _ = cv2.findContours(img_th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭検出
        cv2.drawContours(img_th, contours, -1, 255, -1)
        return img_th

    @staticmethod
    def _invert(img_th):
        """ネガポジ変換"""
        return cv2.bitwise_not(img_th)

    def _erode(self, img_th):
        """エロード処理"""
        return cv2.erode(img_th, self._kernel, iterations=1)


if __name__ == '__main__':
    import time

    path = ""

    threshold_ = 500
    min_length_ = 500
    max_gap_ = 30

    n = np.fromfile(path, dtype=np.uint8)
    img_ = cv2.imdecode(n, cv2.IMREAD_COLOR)
    height_, width_ = img_.shape[:2]

    load = LoadPerspectiveNumFile()
    pre = Preprocess(width_, height_)
    pers = PerspectiveTransformer(width_, height_, load.pts)

    start = time.time()
    img_trans_rot_ = pre.preprocessing(img_, min_length_, threshold_)
    stop = time.time()
    print(stop-start)

    cv2.namedWindow("img", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("img", 1200, 900)
    cv2.imshow("img", img_trans_rot_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    cv2.imwrite("preprocessing.png", img_trans_rot_)
