import numpy as np
import cv2


class EdgeGetter:  # TODO: エッジではなく直線検出では。
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

    threshold_ = 500
    min_length_ = 500

    path_ = r""
    n = np.fromfile(path_, dtype=np.uint8)
    img_orig_ = cv2.imdecode(n, cv2.IMREAD_COLOR)
    height_, width_ = img_orig_.shape[:2]

    # TODO: ここではEdgeGetter()に関してだけ書けばいいので、Preprocessは要らない
    pre = Preprocess(width_, height_)
    edge = EdgeGetter()

    img_th_ = pre._img_pre_process(img_orig_)
    lines_, min_length_, threshold_ = edge.detect_line(img_th_, min_length_, threshold_)
    print(lines_)
    print(min_length_)
    print(threshold_)

    cv2.namedWindow("img_th_", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("img_th_", 1200, 900)
    cv2.imshow("img_th_", img_th_)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
