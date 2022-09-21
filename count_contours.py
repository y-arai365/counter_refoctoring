import cv2
import numpy as np


def morphology(img, kernel_size, method):
    """
    モルフォロジー変換をまとめた関数
    カーネルサイズとメソッドを与えて画像を変更する
    :param img: 画像
    :param kernel_size: カーネルサイズ
    :param method: 変換方法
    :return: 変換後の画像
    """
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    if method == "dilate":
        dst = cv2.dilate(img, kernel, iterations=1)
    elif method == "erode":
        dst = cv2.erode(img, kernel, iterations=1)
    elif method == "opening":
        dst = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
    elif method == "closing":
        dst = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    else:
        dst = img

    return dst


def remove_black(img_hsv, upper_s=70, upper_v=50):
    """黒い部分 = マーキング部分を抽出、反転。"""
    img_black = cv2.inRange(img_hsv, lowerb=(0, 0, 0), upperb=(180, upper_s, upper_v))
    return cv2.bitwise_not(img_black)


def remove_background(img_hsv):
    """彩度の差で、背景を取り除いた製品部分を抽出"""
    img_s = cv2.split(img_hsv)[1]
    return cv2.threshold(img_s, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)[1]


def remove_edge(img, blur_size=15, sobel_size=15):
    """ソーベルフィルタによってエッジを検出し、製品と製品の隙間を抽出、反転。副次的にマーキングの輪郭も検出。"""
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_smooth = cv2.GaussianBlur(img_gray, (blur_size, blur_size), 0)

    # 縦横それぞれでエッジを抽出
    img_sobel_x = cv2.Sobel(img_smooth, cv2.CV_64F, 1, 0, ksize=sobel_size)
    img_sobel_y = cv2.Sobel(img_smooth, cv2.CV_64F, 0, 1, ksize=sobel_size)
    # 検出したエッジを0~255にスケーリング
    img_sobel_x = cv2.convertScaleAbs(img_sobel_x, alpha=255/img_sobel_x.max())
    img_sobel_y = cv2.convertScaleAbs(img_sobel_y, alpha=255/img_sobel_y.max())

    # 縦横のエッジの和を取る
    img_sobel_xy = cv2.bitwise_or(img_sobel_x, img_sobel_y)
    return cv2.threshold(img_sobel_xy, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)[1]


def count_contours(img, erode_size=5, dilate_size=3, thresh_area=100):
    """
    輪郭を取得して、カウントする
    :param img: 元画像
    :param erode_size: 収縮のカーネルサイズ
    :param dilate_size: 膨張のカーネルサイズ
    :param thresh_area: 閾値
    :return:
    """
    erode_size = 2 * erode_size + 1
    dilate_size = 2 * dilate_size + 1

    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    img_without_black = remove_black(img_hsv)

    img_without_bg = remove_background(img_hsv)

    img_without_edge = remove_edge(img)

    # マーキングもなく背景もなく隙間もない = 製品のみ残った2値画像
    img_th = cv2.bitwise_and(img_without_black, img_without_bg)
    img_th = cv2.bitwise_and(img_th, img_without_edge)

    # 膨張収縮によって、輪郭1つ1つを分離する
    img_th = morphology(img_th, erode_size, "erode")
    img_th = morphology(img_th, dilate_size, "dilate")

    # 輪郭の取得
    contours, _ = cv2.findContours(img_th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    result_count = 0
    # 閾値*10以上の輪郭を正の輪郭とする
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > thresh_area*10:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(img, [box], -1, (0, 255, 0), 4)
            result_count += 1

    return img, result_count


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    n = np.fromfile(path, dtype=np.uint8)  # 日本語を含むファイルを扱う
    img_ = cv2.imdecode(n, cv2.IMREAD_COLOR)  # ファイルのデコード
    img_, count = count_contours(img_)

    cv2.namedWindow("result", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("result", 1200, 900)
    cv2.imshow("result", img_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
