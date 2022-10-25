from decimal import Decimal, ROUND_DOWN, ROUND_UP
import math

import cv2
import numpy as np
from PIL import Image

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
        try:  # TODO: tryの中にたくさん書きすぎ。例外処理が必要な箇所のみtryの中に。
            # 直線を検出、そのときの閾値・最小直線距離を取得
            lines, min_length, threshold = self._detect_line(img_canny, first_min_length, first_threshold)
            if lines is None:
                img_trans_rot = img
                return img_trans_rot
            deg_list = self._list_of_degree(lines)

            result_deg = self._get_result_deg(deg_list, img_canny, min_length, threshold)
            img_trans = self.perspective.transform(img)
            img_trans_rot = self._rotation(img_trans, result_deg)

        except Exception as err:  # TODO: Exceptionで受けない。あらゆるエラーをキャッチしちゃうので、想定外のエラーを握りつぶしてしまう
            # TODO: import文はファイル冒頭に。
            import traceback
            import datetime
            import os
            error_dir = "./preprocessing_error/"  # TODO: ハードコーディングしない。
            os.makedirs(error_dir, exist_ok=True)
            now = datetime.datetime.now()
            str_now = "{0:%m%d_%H%M}".format(now)
            file_name = error_dir + str_now + ".txt"
            # TODO: ???。with内でtraceback.print_excすればいいのでは？
            with open(file_name, "w") as f:
                pass
            traceback.print_exc(file=open(file_name, "a"))
            img_trans_rot = img
        finally:  # TODO: finally節は必要か？
            result = img_trans_rot
        return result

    def _image_pre_process(self, image):  # TODO: imageかimgか統一してほしい。
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
                    threshold -= 50  # TODO: マジックナンバー。ハードコーディングしない。
            if lines is None:
                min_length -= 50  # TODO: マジックナンバー。ハードコーディングしない。
        return None, min_length, threshold

    def _list_of_degree(self, lines):
        """linesを基にして、傾いている角度のリスト取得"""
        deg_list = []

        # TODO setなんか使えばもっと簡潔に書けそう。
        for line in lines:
            x1, y1, x2, y2 = line[0]
            deg = self._degree(x1, y1, x2, y2)  # 角度を求める
            if deg not in deg_list:  # 角度がかぶっている場合はスルー
                deg_list.append(deg)
        return deg_list

    def _get_result_deg(self, deg_list, img_canny, min_length, threshold):
        """角度のリストから条件に合う角度を取得"""
        result_deg = None
        for deg in deg_list[:10]:  # TODO: マジックナンバー
            img_canny_rot = self._rotation(img_canny, deg)
            horizontal_lines, _, _ = self._detect_line(img_canny_rot, min_length, threshold)
            if horizontal_lines is not None:  # 直線が検出できた場合
                horizontal_deg_list = []
                for horizontal_line in horizontal_lines:
                    horizontal_deg_list = self._list_of_rounded_angles(horizontal_line, horizontal_deg_list)
                # 正しく回転している場合は-0.5~0.5の角度以外は検出されない(?)  # TODO: 0.5という値はnp.pi/720と関係が？その場合変数に置くべき。
                # TODO: if len(horizontal_deg_list > 0 は、if horiontal_deg_list と書ける。ただし、リストの場合のみ。numpyはダメ。
                if len(horizontal_deg_list) > 0 and np.all(np.array(horizontal_deg_list) <= 0.5) \
                        and np.all(np.array(horizontal_deg_list) >= -0.5):  # TODO: -0.5 <= X <= 0.5 と書ける
                    result_deg = deg
                    break
        if result_deg is None:
            result_deg = self._get_median(deg_list)
        return result_deg

    @staticmethod
    def _rotation(img, deg):
        """画像の回転"""
        # TODO: pillowに変換して回転するよりアフィン変換の方が高速だったはず。
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
        return cv2.Canny(img, 100, 200)  # TODO: マジックナンバー

    def _morphology_close(self, img_th):
        """クロージング処理"""
        return cv2.morphologyEx(img_th, cv2.MORPH_CLOSE, self._kernel)

    @staticmethod
    def _draw_contours(img_th):
        """エッジの穴埋め"""
        img_th_copy = img_th.copy()
        contours, hierarchy = cv2.findContours(img_th_copy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭検出  # TODO: 使わない返り値はアンダースコアに
        # TODO: cv2.drawContours(img_th_copy, contours, -1, 255, -1) で一行で書けるはず。
        for cnt in contours:
            cv2.drawContours(img_th_copy, [cnt], -1, 255, -1)
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
        # TODO: 速度的に大幅に不利とかじゃなければ、わざわざmathをインポートせずにnumpyで書いちゃったほうがいいかも。
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
        deg = self._degree(x1, y1, x2, y2)
        if deg < 0:  # TODO: 場合わけが必要なのか。パッと見、必要なさそうだが。必要なら理由をコメントしておいてほしい
            deg_decimal = Decimal(str(deg)).quantize(Decimal("0.1"), rounding=ROUND_DOWN)  # TODO: なぜstr(deg)？
            deg = float(deg_decimal)
        else:
            deg_decimal = Decimal(str(deg)).quantize(Decimal("0.1"), rounding=ROUND_UP)
            deg = float(deg_decimal)
        if deg != -45.0 and deg != 45.0:  # TODO: イマイチ何をしてるのか判然としない。45, -45度以外の内重複してないものを元のリストに追加？なぜ？
            if deg not in deg_list:
                deg_list.append(deg)
        return deg_list

    @staticmethod
    def _get_median(deg_list):
        """角度リストの中央値取得"""
        # TODO: np.absで一発
        deg_abs_list = []
        for _deg in deg_list:
            deg_abs_list.append(abs(_deg))

        # TODO: 可読性低し。絶対値が最も小さいものと30以上距離が離れているものは削除、ということ？
        # TODO: deg_abs_listがnumpy.ndarrayであれば、(deg_abs_list - deg_min) > 30とすればインデックスが取得できるはず。
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
