# -*- coding: utf-8 -*-
"""
製品検出のみを行う
"""
import sys
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool as Pool

import cv2
import numpy as np


def binarize(img):
    """
    2値化
    """
    ret, img_thresh = cv2.threshold(img, 0, 255, cv2.THRESH_OTSU)
    return img_thresh, ret


def template_match(arg):
    img, img_gray, path, name, matching_threshold, hls_range = arg

    file_name = path + name
    # ファイル名に日本語が含まれている場合を考慮して、デコードして画像を読み込む
    n_name = np.fromfile(file_name, np.uint8)
    pattern = cv2.imdecode(n_name, cv2.IMREAD_COLOR)

    hls_range.set_range(pattern)  # パターン画像でHLSの範囲を設定

    pattern = cv2.cvtColor(pattern, cv2.COLOR_BGR2GRAY)
    h, w = pattern.shape[:2]
    transpose = 0
    # パターンが縦長になるように回転する
    if h < w:
        pattern = pattern.transpose(1, 0)  # 軸の順番を入れ替える
        pattern = pattern[:, ::-1]  # 順番の変更により反転している部分を直す
        h, w = pattern.shape[:2]
        img = img.transpose(1, 0, 2)  # 軸の順番を入れ替える
        img = img[:, ::-1]  # 順番の変更により反転している部分を直す
        img_gray = img_gray.transpose(1, 0)  # 軸の順番を入れ替える
        img_gray = img_gray[:, ::-1]  # 順番の変更により反転している部分を直す
        transpose = 1
    img_h, img_w = img.shape[:2]
    try:
        result = cv2.matchTemplate(img_gray, pattern, cv2.TM_CCOEFF_NORMED)
    except:
        result = np.float32([[0., 0., 0.]])
    finally:
        loc = np.where(result >= matching_threshold)
        black = np.zeros((img_h, img_w), np.uint8)
        miss_pattern = 0
        exact_pattern = 0
        prev_pattern_y = 0
        exact_list = []
        miss_list = []
        # 結果を黒画像に描画する
        for top_left_x, top_left_y in zip(*loc[::-1]):
            img_trim = img[top_left_y:top_left_y+h, top_left_x:top_left_x+w]  # マッチング領域を切り取り

            if hls_range.in_range(img_trim):  # HLSの平均が範囲に入っていたら

                pattern_slip = top_left_y - prev_pattern_y  # マッチングした部分のズレを計算
                pattern_thresh = h / 5  # マッチング部分を描画するかどうかの閾値
                if pattern_thresh < pattern_slip < h - pattern_thresh:  # ex) pattern_h=100px　10<pattern_slip<90
                    miss_pattern += 1
                    miss_list.append((top_left_x, top_left_y))
                elif pattern_slip > h - pattern_thresh:  # マッチングのずれが閾値より大きいとき
                    top_left = (top_left_x, top_left_y)
                    bottom_right = (top_left_x+w, top_left_y+h)
                    cv2.rectangle(black, top_left, bottom_right, 255, -1)
                    exact_pattern += 1
                    prev_pattern_y = top_left_y
                    exact_list.append((top_left_x, top_left_y))
                else:  # その他
                    top_left = (top_left_x, top_left_y)
                    bottom_right = (top_left_x+w, top_left_y+h)
                    cv2.rectangle(black, top_left, bottom_right, 255, -1)
                    exact_pattern += 1
                    exact_list.append((top_left_x, top_left_y))

        # 正しい領域を描画できていなかった場合
        for num, top_left in enumerate(miss_list):
            top_left_x, top_left_y = top_left
            for i in range(5):
                # 縦1px×横w/2-2の四角が黒ならば、その部分は正しい領域。白が少しでも含まれるならば、不要または誤った領域。
                color = black[top_left_y+i-1:top_left_y+i, top_left_x+2:int(top_left_x + (w/2))]
                # 領域全体が黒の場合
                if np.sum(color) == 0:
                    # missからexactへ結果を移動する
                    bottom_right = (top_left_x+w, top_left_y+h)
                    cv2.rectangle(black, top_left, bottom_right, 255, -1)
                    exact_pattern += 1
                    miss_pattern -= 1
                    exact_list.append((top_left_x, top_left_y))
                    break

        # くっついた領域を離すために黒枠を描画する
        for top_left_x, top_left_y in exact_list:
            top_left = (top_left_x, top_left_y)
            bottom_right = (top_left_x+w, top_left_y+h)
            cv2.rectangle(black, top_left, bottom_right, 0, 3)

        # 回転していた場合戻す
        if transpose == 1:
            black = black.transpose(1, 0)  # 軸の順番を入れ替える
            black = black[::-1]  # 順番の変更により反転している部分を直す

        # 描画した黒画像を使用して輪郭検出
        contours, hierarchy = cv2.findContours(black, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        result = (name, contours, black, exact_pattern, miss_pattern)
        return result


def matching(img, path, matching_threshold, hls_range):
    """
    パターン画像の中で最も正しくマッチングするものを求めてその結果を、黒画像に白矩形で描画する
    img: 画像
    path: パターン画像の入っているディレクトリ
    matching_threshold: パターンマッチングの閾値
    return: black_gray: 最適なパターンでマッチングし、その場所を黒画像に白矩形を描画したもの
    return: most_p_w, most_p_h: 最適なパターンのwidth, height
    """
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 最も正しくマッチングするパターン画像を探す
    most_file = None
    # multiprocessingで立てるプロセス数(スレッド数)
    cv2.setNumThreads(4)
    try:
        # プロセスとなるtemplate_match関数とはQueueを介して結果をやり取りする
        cpu = cpu_count()
        p = Pool(cpu)
        args = [(img, img_gray, path, "pattern1.jpg", matching_threshold, hls_range),
                (img, img_gray, path, "pattern2.jpg", matching_threshold, hls_range),
                (img, img_gray, path, "pattern3.jpg", matching_threshold, hls_range),
                (img, img_gray, path, "pattern4.jpg", matching_threshold, hls_range)]
        result_list = p.map(template_match, args)
        count_list = []
        # 1つもマッチングしなかったものは排除する
        for count_result in result_list:
            if count_result[3] != 0:  # exact_cout != 0
                count_list.append(count_result)
        # リストの長さによって処理を分ける
        if len(count_list) == 0:  # マッチング結果が1つもなければ誤りなので、エラー処理に飛ぶ
            raise Exception
        elif len(count_list) == 1:  # マッチング結果が1つならばそれが正解
            most_file = count_list[0][0]
            black_gray = count_list[0][2]
        elif len(count_list) == 2:  # マッチング結果が2つならば、exact_countが多いものが正解
            if count_list[0][3] > count_list[1][3]:
                most_file = count_list[0][0]
                black_gray = count_list[0][2]
            else:
                most_file = count_list[1][0]
                black_gray = count_list[1][2]
        elif len(count_list) > 2:  # マッチング結果が4つならば(3つも含むが3は現状見ていない)、contoursが多いものが正解
            max_len_cnt = 0
            for count_result in count_list:
                if len(count_result[1]) > max_len_cnt:
                    max_len_cnt = len(count_result[1])
                    most_file = count_result[0]
                    black_gray = count_result[2]
        # ファイル名に日本語が含まれている場合を考慮して、デコードして画像を読み込む
        file_name = path + most_file
        n_name = np.fromfile(file_name, np.uint8)
        most_pattern = cv2.imdecode(n_name, cv2.IMREAD_COLOR)
        most_p_h, most_p_w = most_pattern.shape[:2]
        return black_gray, most_p_w, most_p_h, most_pattern
    # エラーが発生した場合(1製品もマッチングしなかった場合もここへ飛ぶ)
    except Exception:
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
        file_name = path + "pattern1.jpg"
        # ファイル名に日本語が含まれている場合を考慮して、デコードして画像を読み込む
        n_name = np.fromfile(file_name, np.uint8)
        most_pattern = cv2.imdecode(n_name, cv2.IMREAD_COLOR)

        hls_range.set_range(most_pattern)  # パターン画像でHLSの範囲を設定

        most_pattern_gray = cv2.cvtColor(most_pattern, cv2.COLOR_BGR2GRAY)
        most_p_h, most_p_w = most_pattern_gray.shape[:2]
        img_h, img_w = img.shape[:2]
        black = np.zeros((img_h, img_w, 3), np.uint8)
        # most_patternを使用して改めてパターンマッチングを行って黒画像に白矩形を描画する
        result = cv2.matchTemplate(img_gray, most_pattern_gray, cv2.TM_CCOEFF_NORMED)
        loc = np.where(result >= matching_threshold)
        for top_left in zip(*loc[::-1]):
            bottom_right = (top_left[0] + most_p_w, top_left[1] + most_p_h)
            img_trim = img[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]]  # マッチング領域を切り取り
            if hls_range.in_range(img_trim):  # HLSの平均が範囲に入っていたら
                cv2.rectangle(black, top_left, bottom_right, (255, 255, 255), -1)
        for top_left in zip(*loc[::-1]):
            bottom_right = (top_left[0] + most_p_w, top_left[1] + most_p_h)
            img_trim = img[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]]  # マッチング領域を切り取り
            if hls_range.in_range(img_trim):  # HLSの平均が範囲に入っていたら
                cv2.rectangle(black, top_left, bottom_right, (0, 0, 0), 3)
        black_gray = cv2.cvtColor(black, cv2.COLOR_BGR2GRAY)
        return black_gray, most_p_w, most_p_h, most_pattern


def trim(img):
    """
    一定ラインの面積を有する輪郭を取得して、その輪郭をすべて含む枠で画像を切り取る
    一定ラインを下回った輪郭でも画角に収まるように、上下左右に200pxずつ余裕をもって切り取る
    img:　黒画像に白矩形を描画したもの
    """
    img_h, img_w = img.shape[:2]
    kernel = np.ones((15, 15), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    xmin = 5000
    xmax = 0
    ymin = 5000
    ymax = 0
    if len(contours) != 0:
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 面積1500以上の輪郭のものを使用
            if area > 1500:
                # 外接矩形の座標の取得
                x, y, w, h = cv2.boundingRect(cnt)
                xleft = x
                xright = x + w
                ytop = y
                ybottom = y + h
                # 輪郭全てを含むように、長方形の座標を求める
                if xleft < xmin:
                    xmin = xleft
                if xright > xmax:
                    xmax = xright
                if ytop < ymin:
                    ymin = ytop
                if ybottom > ymax:
                    ymax = ybottom
        # 上下左右200pxの余白を作る
        xmin = xmin - 200
        ymin = ymin - 200
        xmax = xmax + 200
        ymax = ymax + 200
        # 余白を作ったことにより、画像内に収まらなければ修正する
        if xmin == 4800:
            xmin = 0
        if ymin == 4800:
            ymin = 0
        if xmax == 200:
            xmax = img_w
        if ymax == 200:
            ymax = img_h
        if xmin == xmax:
            xmin = 0
            ymin = 0
            xmax = img_w
            ymax = img_h
        if ymin == ymax:
            xmin = 0
            ymin = 0
            xmax = img_w
            ymax = img_h
        if xmin < 0:
            xmin = 0
        if ymin < 0:
            ymin = 0
    # 輪郭がなければ、画像は切り取らない
    else:
        xmin = 0
        ymin = 0
        xmax = img_w
        ymax = img_h
    return xmin, xmax, ymin, ymax


def count(img, black, area_threshold):
    """
    blackから輪郭を取り出して、threshold以上のものを検出した輪郭としてimgに描画
    またその輪郭個数を返す
    img: 検出物画像
    black: 黒画像に白矩形を描画したもの
    area_threshold: パターンのサイズから割り出した輪郭が正しい検出かどうか判断する閾値
    """
    contours, hierarchy = cv2.findContours(black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_h, img_w = img.shape[:2]
    gray = np.ones((img_h, img_w, 3), np.uint8) * 100
    new_cons = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > area_threshold:
            new_cons.append(cnt)

    gray = cv2.drawContours(gray, new_cons, -1, (30, 255, 0), -1)
    gray = cv2.drawContours(gray, new_cons, -1, (30, 255, 0), 2)
    is_count = len(new_cons)

    result = cv2.addWeighted(img, 0.5, gray, 0.5, 0)

    return result, is_count


def matching_pattern(dir_path, img_rot, matching_threshold, hls_range):
    """
    画像を射影変換し、回転する
    その後、最適パターン画像を探し、製品検出結果を返す
    dir_path: パターン4枚が含まれるディレクトリ
    img_rot: 射影変換、回転後の画像
    matching_threshold: パターンマッチングの閾値
    hls_range: HLSRange
    """
    black, p_w, p_h, pattern = matching(img_rot, dir_path, matching_threshold, hls_range)
    xmin, xmax, ymin, ymax = trim(black)
    img_rot = img_rot[ymin:ymax, xmin:xmax]
    black = black[ymin:ymax, xmin:xmax]
    pattern_gray = cv2.cvtColor(pattern, cv2.COLOR_BGR2GRAY)
    patern_th, ret = binarize(pattern_gray)
    contours, hierarchy = cv2.findContours(patern_th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    max_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > max_area:
            max_area = area
    area_threshold = int(max_area / 5)

    result, is_count = count(img_rot, black, area_threshold)

    return result, is_count, img_rot, p_w, p_h, pattern, black


if __name__ == "__main__":
    import preprocessing_

    from hls_range import HLSRange

    image_path = sys.argv[1]
    hls_range_ = HLSRange(40, 40, 40)
    n = np.fromfile(image_path, dtype=np.uint8)
    image = cv2.imdecode(n, cv2.IMREAD_COLOR)
    pattern_dir_path = sys.argv[2]
    if len(sys.argv) == 5:
        color = sys.argv[3]
        img_rotate = preprocessing_.preprocessing(image)
    else:
        color = "blue"
        img_rotate = preprocessing_.preprocessing(image)
    result_img, is_count_num, _, _, _, _, _ = matching_pattern(pattern_dir_path, img_rotate, 0.85, hls_range_)

    cv2.imwrite("result_img.jpg", result_img)

