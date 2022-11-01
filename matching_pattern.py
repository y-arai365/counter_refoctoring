"""
製品検出のみを行う
"""
from multiprocessing.pool import ThreadPool as Pool

import cv2
import numpy as np


class Matching:
    def __init__(self, threshold):
        """
        回転した画像とパターン画像をマッチングするクラス
        Args:
            threshold (float): 製品を検出するときの閾値
        """
        self.threshold = threshold

        self._pattern_1_file_name = "pattern1.jpg"
        self._pattern_2_file_name = "pattern2.jpg"
        self._pattern_3_file_name = "pattern3.jpg"
        self._pattern_4_file_name = "pattern4.jpg"

        self.pattern_img = None

    def get_res(self, img_rot, dir_path):
        """
        回転画像にテンプレートマッチングをかけて、マッチした製品を緑で描画した画像とその製品数を返す

        Args:
            img_rot (img_bgr): 回転画像
            dir_path (string): パターン画像の保存先、フォルダ名

        Returns:
            img_th, img_bgr: マッチング結果画像、パターン画像
        """
        pattern_img = self._choose_suitable_pattern_img(img_rot, dir_path)
        return self._template_match(img_rot, pattern_img), pattern_img

    def _choose_suitable_pattern_img(self, img_rot, dir_path):
        """
        複数あるパターン画像から適切なものを選ぶ

        Args:
            img_rot (img_bgr): 回転画像
            dir_path (string): パターン画像の保存先、フォルダ名

        Returns:
            img_bgr: マッチングに使うパターン画像
        """
        p = Pool(4)
        args = [(img_rot, self._get_pattern_image(dir_path + self._pattern_1_file_name)),
                (img_rot, self._get_pattern_image(dir_path + self._pattern_2_file_name)),
                (img_rot, self._get_pattern_image(dir_path + self._pattern_3_file_name)),
                (img_rot, self._get_pattern_image(dir_path + self._pattern_4_file_name))]
        count_and_pattern_img_list = p.map(self._get_matching_count_and_pass_pattern_img, args)
        count_list = [count_and_pattern_img[0] for count_and_pattern_img in count_and_pattern_img_list]
        max_value = max(count_list)
        max_index = count_list.index(max_value)
        pattern_img = count_and_pattern_img_list[max_index][1]
        return pattern_img

    @staticmethod
    def _get_pattern_image(file_name):
        """パターン画像の取得"""
        return cv2.imread(file_name)

    def _get_matching_count_and_pass_pattern_img(self, arg):
        """
        回転後画像とパターン画像のテンプレートマッチングの計数結果とファイル名を返す
        並列処理により4回処理される

        Args:
            arg ([(img_bgr, img_bgr),]): 回転後画像、パターン画像

        Returns:
            int, img_bgr: カウント数(1つのパターン画像にいくつも矩形が表示されるので実際の製品数ではない)、パターン画像
        """
        img_rot, pattern_img = arg
        img_rot_gray = cv2.cvtColor(img_rot, cv2.COLOR_BGR2GRAY)
        pattern_img_gray = cv2.cvtColor(pattern_img, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(img_rot_gray, pattern_img_gray, cv2.TM_CCOEFF_NORMED)
        match_count = np.count_nonzero(result >= self.threshold)
        return match_count, pattern_img

    @staticmethod
    def _template_match(img_rot, pattern):
        """
        BGR画像2枚を使ってテンプレートマッチング、グレースケールの方が検出しやすいため変換

        Args:
            img_rot (img_bgr): 全体画像
            pattern (img_bgr): パターン画像

        Returns:
            img_th: マッチング結果画像
        """
        img_rot_gray = cv2.cvtColor(img_rot, cv2.COLOR_BGR2GRAY)
        pattern_gray = cv2.cvtColor(pattern, cv2.COLOR_BGR2GRAY)
        return cv2.matchTemplate(img_rot_gray, pattern_gray, cv2.TM_CCOEFF_NORMED)


class ResultImage:
    def __init__(self, k_size, threshold, margin_of_matching_range=200,
                 threshold_of_matching_cover=100, color_drawing_match_result=(30, 255, 0)):
        """
        マッチングの結果を画像に描画するクラス

        Args:
            k_size (int): 二値化画像をモルフォロジー変換するときのカーネル値
            threshold (float): 製品を検出するときの閾値
        """
        self.threshold = threshold

        self._kernel = np.ones((k_size, k_size), np.uint8)

        self._margin_of_matching_range = margin_of_matching_range
        self._threshold_of_matching_cover = threshold_of_matching_cover
        self._color_drawing_match_result = color_drawing_match_result

    def get_result_img_and_count_result(self, img_rot, res, pattern_img):
        """
        回転画像にテンプレートマッチングをかけて、マッチした製品を緑で描画した画像とその製品数を返す

        Args:
            img_rot (img_bgr): 回転画像
            res (img_th): マッチング結果画像
            pattern_img (img_bgr): パターン画像

        Returns:
            img_bgr, int: 結果描画後の画像、計数結果
        """
        pattern_h, pattern_w = pattern_img.shape[:2]
        black_back = self._get_black_back(img_rot)
        img_black_back_and_white_rect = self._get_img_black_back_and_white_rect(res, black_back, pattern_w, pattern_h)
        x_min, x_max, y_min, y_max = self._get_trim_coordinates(img_black_back_and_white_rect)
        img_rot = img_rot[y_min:y_max, x_min:x_max]
        img_black_back_and_white_rect = img_black_back_and_white_rect[y_min:y_max, x_min:x_max]
        new_cons = self._get_contours(img_black_back_and_white_rect)
        count_result = len(new_cons)
        result_img = self._draw_contours(img_rot, new_cons)
        return result_img, count_result

    @staticmethod
    def _get_black_back(img_rot):
        """
        黒背景作成

        Args:
            img_rot (img_bgr): 回転させた画像

        Returns:
            img_th: 黒画像
        """
        h, w = img_rot.shape[:2]
        black_back = np.zeros((h, w))
        return black_back.astype(np.uint8)

    def _get_img_black_back_and_white_rect(self, res, black, w, h):
        """
        resをもとにマッチングした位置を白くした黒画像を作成

        Args:
            res (img_th): cv2.matchTemplateの出力結果
            black (img_th): 黒背景画像、回転画像がもと
            w (int): パターン画像の幅
            h (int): パターン画像の高さ

        Returns:
            img_th: マッチング範囲を白い矩形に変えた黒画像
        """
        loc = np.where(res >= self.threshold)
        for pt in zip(*loc[::-1]):
            cv2.rectangle(black, pt, (pt[0] + w, pt[1] + h), 255, -1)
            black = self._add_gap(black, pt, (pt[0] + w, pt[1] + h))
        return black

    def _get_trim_coordinates(self, img_th):
        """
        白矩形付き黒画像から白矩形全体を囲うような範囲を取得し、そこから前後左右200pxずつ広げた点を取得する

        Args:
            img_th (img_th): 白矩形付き黒画像

        Returns:
            (int, int, int, int) : トリミング範囲(左上x, 右下x, 左上y, 右下y)
        """
        img_h, img_w = img_th.shape
        img_th = cv2.morphologyEx(img_th, cv2.MORPH_CLOSE, self._kernel)
        contours, _ = cv2.findContours(img_th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours != 0:
            contour = np.vstack(contours)
            x, y, w, h = cv2.boundingRect(contour)
            x_left = x
            x_right = x + w
            y_top = y
            y_bottom = y + h

            x_min = max(x_left - self._margin_of_matching_range, 0)
            y_min = max(y_top - self._margin_of_matching_range, 0)
            x_max = min(x_right + self._margin_of_matching_range, img_w)
            y_max = min(y_bottom + self._margin_of_matching_range, img_h)
        else:  # 輪郭の取得ができなかったとき
            x_min = 0
            y_min = 0
            x_max = img_w
            y_max = img_h
        return x_min, x_max, y_min, y_max

    def _get_contours(self, black):
        """
        白矩形付き黒画像から一定の閾値(面積)以上の輪郭を取得

        Args:
            black (img_th): 白矩形付き黒画像

        Returns:
            list[np.ndarray(shape=(x, 4, 1, 2), dtype=np.int32),]: 一定の閾値以上の輪郭のリスト
        """
        contours, _ = cv2.findContours(black, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        area_threshold = self._find_threshold(contours)
        new_cons = [cnt for cnt in contours if cv2.contourArea(cnt) > area_threshold]
        return new_cons

    def _draw_contours(self, img, new_cons):
        """
        輪郭リストを基に回転画像に検出位置を描画

        Args:
            img (img_bgr): 回転画像
            new_cons (list[np.ndarray(shape=(x, 4, 1, 2), dtype=np.int32),]): 輪郭のリスト

        Returns:
            img_bgr: 検出位置を緑の矩形で描画して示した画像
        """
        img_h, img_w = img.shape[:2]
        gray = np.ones((img_h, img_w, 3), np.uint8) * self._threshold_of_matching_cover
        gray = cv2.drawContours(gray, new_cons, -1, self._color_drawing_match_result, -1)
        result = cv2.addWeighted(img, 0.5, gray, 0.5, 0)
        return result

    @staticmethod
    def _add_gap(black, top_left, bottom_right):
        """
        白矩形付き黒画像の矩形同士がくっついているかもしれないので、黒い矩形を描画して切り離す
        Args:
            black (img_th): 白矩形付き黒画像
            top_left (): 白矩形の左上
            bottom_right (): 白矩形の右下

        Returns:
            img_th: 白矩形付き黒画像(白矩形同士にくっつき除去)
        """
        return cv2.rectangle(black, top_left, bottom_right, 0, 3)

    @staticmethod
    def _find_threshold(contours):  # 閾値の返り値が各cntの1/5に必ずなる→_count関数でif area > area_threshold:してる意味がない(ノイズ除去？)
        """
        黒画像内で面積が最大の白領域の1/5を製品検出時の閾値にする

        Args:
            contours (list[np.ndarray(shape=(x, 4, 1, 2), dtype=np.int32),]): 輪郭のリスト

        Returns:
            int: 製品検出時の閾値
        """
        area_list = [cv2.contourArea(cnt) for cnt in contours]
        max_area = max(area_list)
        return int(max_area / 5)


if __name__ == "__main__":
    from preprocessing import Preprocess
    import time

    path_ = ""
    dir_path_ = ""

    threshold_ = 500
    min_length_ = 500
    matching_threshold_ = 0.85

    n = np.fromfile(path_, dtype=np.uint8)
    img_ = cv2.imdecode(n, cv2.IMREAD_COLOR)
    height, width = img_.shape[:2]
    pre = Preprocess(width, height)
    match_ = Matching(threshold=matching_threshold_)
    res_img_ = ResultImage(k_size=15, threshold=matching_threshold_)

    img_rot_ = pre.preprocessing(img_, min_length_, threshold_)

    start = time.time()
    res_, pattern_img_ = match_.get_res(img_rot_, dir_path_)
    result_, is_count_ = res_img_.get_result_img_and_count_result(img_rot_, res_, pattern_img_)
    print(is_count_)

    stop = time.time()
    print(stop-start)

    cv2.namedWindow("_rot", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("_rot", 1200, 900)
    cv2.imshow("_rot", result_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
