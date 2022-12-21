import numpy as np
import cv2


class PerspectiveTransformer:
    def __init__(self, cam_width, cam_height, points, box_width=4, box_height=3, dx=320):
        """
        :param cam_width: Int カメラ画像の幅
        :param cam_height: Int カメラ画像の高さ
        :param points: Array(shape=(4, 2)) 紙に描かれた長方形を撮影したときの、その頂点の座標
        :param box_width: 紙に描かれた長方形の幅の、「実際の」長さ。もしくは比
        :param box_height: Int/Float 紙に描かれた長方形の高さの、「実際の」長さ。もしくは比
        :param dx:

                         ← dx →
                      ↑ ┌───────────────────────────────────────┐
                     dy │                                       │
                      ↓ │                                       │
                        │      *                         *      │
                        │            .              .           │
                        │                                       │
                        │                                       │
                        │                                       │
                        │         .                    .        │
                        │                                       │
                        │      *                         *      │
                      ↑ │                                       │           * : dst_points
                     dy │                                       │           . : points
                      ↓ └───────────────────────────────────────┘

        """
        # 撮影した紙上の長方形の縦横と同じ比になるような、画像上の点の座標を計算。射影変換の目的地となる座標。
        box_aspect_ratio = box_width / box_height
        dy = PerspectiveTransformer._dy(cam_width, cam_height, box_aspect_ratio, dx)
        dst_points = PerspectiveTransformer._points_for_perspective_transform(dx, dy, cam_width, cam_height)

        # 撮影した長方形の画像上での座標を、上で計算した座標へと移動させる射影変換行列
        matrix = PerspectiveTransformer._perspective_matrix(points, dst_points)

        # その変換行列で変換すると、画像の4隅がどこへ行くか
        corners_transformed = PerspectiveTransformer._transformed_img_corners(cam_width, cam_height, matrix)

        # 画像がはみ出ないように、射影変換後の画像の左上の点が原点に来るよう平行移動。
        x = corners_transformed[0, 0]
        y = corners_transformed[0, 1]
        self._matrix = PerspectiveTransformer._shift_perspective_matrix(matrix, x, y)

        # 変換後の画像サイズ
        self.width, self.height = PerspectiveTransformer._transformed_image_size(corners_transformed)

    def transform(self, img, border_value=(0, 0, 0)):
        """射影変換。変換後、画像が切れないように平行移動も合成ずみ。"""
        return cv2.warpPerspective(img, self._matrix, (self.width, self.height), borderValue=border_value)

    @staticmethod
    def _dy(cam_width, cam_height, box_aspect_ratio, dx):
        dy = (dx / box_aspect_ratio) + (cam_height - cam_width / box_aspect_ratio) / 2
        return round(dy)

    @staticmethod
    def _points_for_perspective_transform(dx, dy, img_width, img_height):
        left_top = [dx, dy]
        left_bottom = [dx, img_height - dy]
        right_bottom = [img_width - dx, img_height - dy]
        right_top = [img_width - dx, dy]
        return np.float32([[left_top, left_bottom, right_bottom, right_top]])

    @staticmethod
    def _transformed_img_corners(img_width, img_height, matrix):
        corners = np.float32([[[0, 0], [0, img_height], [img_width, img_height], [img_width, 0]]])
        corners_transfomed = cv2.perspectiveTransform(corners, matrix)
        return corners_transfomed.squeeze()

    @staticmethod
    def _perspective_matrix(points, dst_points):
        return cv2.getPerspectiveTransform(np.float32(points), np.float32(dst_points))

    @staticmethod
    def _shift_perspective_matrix(matrix, x, y):
        matrix[0, 2] -= x
        matrix[1, 2] -= y
        return matrix

    @staticmethod
    def _transformed_image_size(corners_transformed):
        x_min = np.min(corners_transformed[:, 0])
        x_max = np.max(corners_transformed[:, 0])
        y_min = np.min(corners_transformed[:, 1])
        y_max = np.max(corners_transformed[:, 1])
        return round(x_max - x_min), round(y_max - y_min)


class LoadPerspectiveNumFile:
    def __init__(self, pers_num_path="pers_num.npy"):
        self.pts = np.load(pers_num_path)[0]


if __name__ == '__main__':
    pers_num_path_ = "pers_num.npy"
    image_path_ = r"pre_.jpg"
    # image_path = r"C:\Users\pc011\Desktop\test\counter\exp-4.jpg"

    pts = np.load(pers_num_path_)[0]
    img_orig = cv2.imread(image_path_)

    height, width = img_orig.shape[:2]

    transformer = PerspectiveTransformer(width, height, pts)
    img_pers = transformer.transform(img_orig)

    cv2.namedWindow("img_pers", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("img_pers", 1200, 900)
    cv2.imshow("img_pers", img_pers)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
