import cv2
import numpy as np


class HLSRange:
    def __init__(self, h_range_width=30, l_range_width=30, s_range_width=30):
        """
        基準となるパターン画像のHLS平均値から上限下限を設定、対象画像のHLS平均が範囲内に入っているかどうかを判定

        Args:
            h_range_width (int): Hチャンネルの色の範囲の幅
            l_range_width (int): Lチャンネルの色の範囲の幅
            s_range_width (int): Sチャンネルの色の範囲の幅
        """
        self.h_range_width = h_range_width
        self.l_range_width = l_range_width
        self.s_range_width = s_range_width

        (self._h_lower1, self._h_upper1), (self._h_lower2, self._h_upper2) = (0, 180), (0, 180)
        self._l_lower, self._l_upper = 0, 255
        self._s_lower, self._s_upper = 0, 255

    def set_range_width(self, h_range, l_range, s_range):
        """
        カラーレンジを変更する関数

        Args:
            h_range (int):
            l_range (int):
            s_range (int):
        """
        self.h_range_width = h_range
        self.l_range_width = l_range
        self.s_range_width = s_range

    def get_range_width(self):
        """
        カラーレンジを取得する関数

        Returns:
            (int, int, int):
        """
        return self.h_range_width, self.l_range_width, self.s_range_width

    def set_range(self, img_pattern):
        """
        パターン画像のHLSの平均値から設定した幅の上限下限を設定

        Args:
            img_pattern (img_bgr): パターン画像

        """
        hue_target, lightness_target, saturation_target = self._get_hls_average(img_pattern)

        self._h_lower1, self._h_upper1, self._h_lower2, self._h_upper2, \
            self._l_lower, self._l_upper, \
            self._s_lower, self._s_upper = \
            self._get_range(hue_target, lightness_target, saturation_target)

    def in_range(self, img_trim_bgr):
        """
        マッチングした箇所のHLSが、指定した範囲に収まっているかどうか。
        すべて収まっていればTrue

        Args:
            img_trim_bgr (img_bgr): マッチングした矩形で切り取った画像

        Returns:
            bool:

        """
        hue_source, lightness_source, saturation_source = self._get_hls_average(img_trim_bgr)

        in_hue_range = self._h_lower1 <= hue_source <= self._h_upper1 or self._h_lower2 <= hue_source <= self._h_upper2
        in_lightness_range = self._l_lower <= lightness_source <= self._l_upper
        in_saturation_range = self._s_lower <= saturation_source <= self._s_upper

        return in_hue_range and in_lightness_range and in_saturation_range

    @staticmethod
    def _get_hls_average(img_bgr):
        img_hls = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HLS)
        return np.mean(img_hls, axis=(0, 1), dtype=int)

    def _get_range(self, h_target, l_target, s_target):
        """
        指定したH,L,Sから上限下限を求める。
        L, Sは通常通り0~255であるが、Hは一般的に0~359を取り、かつ円環状なのでh_range_widthが取りうる範囲は±180で十分であり、
        (10±180 -> -170~190 -> 190~360 or 0~190 / 350±180 -> 170~530 -> 170~360 or 0~170)
        さらにOpenCVにおけるHは0~179となるので±90となるよう、1/2して使っている。
        また、0以下もしくは179,255以上になることがあるが、範囲内にあるかどうか判定できればいいので気にしていない。

        Args:
            h_target (int): [0~180]
            l_target (int): [0~255]
            s_target (int): [0~255]

        Returns:
            (int, int, int, int, int, int, int, int)

        """
        h_lower1, h_upper1 = int(round(h_target - self.h_range_width/2)), int(round(h_target + self.h_range_width/2))
        if h_lower1 < 0:
            n = 180
        elif h_upper1 > 180:
            n = -180
        else:
            n = 0
        h_lower2, h_upper2 = h_lower1 + n, h_upper1 + n

        l_lower, l_upper = l_target - self.l_range_width, l_target + self.l_range_width
        s_lower, s_upper = s_target - self.s_range_width, s_target + self.s_range_width

        return h_lower1, h_upper1, h_lower2, h_upper2, l_lower, l_upper, s_lower, s_upper


if __name__ == '__main__':
    img_target = np.array([[[32, 64, 128]]], np.uint8)   # H: 10, L: 80, S:153
    # img_target = np.array([[[64, 32, 128]]], np.uint8)   # H:170, L: 80, S:153
    # img_target = np.array([[[190, 190, 64]]], np.uint8)  # H: 90, L:127, S:126
    h, l, s = cv2.cvtColor(img_target, cv2.COLOR_BGR2HLS)[0, 0]
    print("img_target\nH:{:3d}, L:{:3d}, S:{:3d}".format(h, l, s))

    img_source = np.array([[[150, 100, 50]]], np.uint8)
    h, l, s = cv2.cvtColor(img_source, cv2.COLOR_BGR2HLS)[0, 0]
    print("img_source\nH:{:3d}, L:{:3d}, S:{:3d}".format(h, l, s))

    print("="*50)
    in_hls_range = HLSRange(180, 255, 255)
    in_hls_range.set_range(img_target)

    print("α :", in_hls_range.get_range_width())
    print(f"H:{in_hls_range._h_lower1:3d}~{in_hls_range._h_upper1:3d} "
          f"or {in_hls_range._h_lower2:3d}~{in_hls_range._h_upper2:3d}")
    print(f"L:{in_hls_range._l_lower:3d}~{in_hls_range._l_upper:3d}")
    print(f"S:{in_hls_range._s_lower:3d}~{in_hls_range._s_upper:3d}")

    in_range = in_hls_range.in_range(img_source)
    print("img_source is{}in the range.".format(" " if in_range else " NOT "))

    print("="*50)
    in_hls_range.set_range_width(40, 40, 40)
    in_hls_range.set_range(img_target)

    print("α :", in_hls_range.get_range_width())
    print(f"H:{in_hls_range._h_lower1:3d}~{in_hls_range._h_upper1:3d} "
          f"or {in_hls_range._h_lower2:3d}~{in_hls_range._h_upper2:3d}")
    print(f"L:{in_hls_range._l_lower:3d}~{in_hls_range._l_upper:3d}")
    print(f"S:{in_hls_range._s_lower:3d}~{in_hls_range._s_upper:3d}")

    in_range = in_hls_range.in_range(img_source)
    print("img_source is{}in the range.".format(" " if in_range else " NOT "))
