from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import os
import pickle
import re
import shutil
import tkinter.filedialog as tkfd
import webbrowser

import cv2
import numpy as np
from PIL import Image, ImageTk

import translate_word
from count_contours import count_contours
from db_manage import DatabaseManage
from hls_range import HLSRange
# from matching_pattern import matching_pattern
from _matching_pattern import PatternImage
from output_html import output_html, LabelHTMLWriter
# from preprocessing import preprocessing
from _preprocessing import Preprocess
from qr_code import QRCodeBase64Generator
from setting_count import load_setting_file
from write_csv import make_csv_file


db_file = "./count/count.db"  # データベースファイルパス
dirs_dir = "./count/"  # count_systemにおけるディレクトリを全て含む元ディレクトリ
dirs = "./count/pattern/"  # パターン画像を保存するディレクトリ
result_dirs = "./count/result/"  # 結果を保存するディレクトリ
log_dirs = "./count/log/"  # ログファイルを保存するディレクトリ
excel_dirs = "./count/report/"  # 出力したエクセルを保存するディレクトリ
setting_dir = "./count/setting/"  # 検出アルゴリズムの設定ファイルを保存するディレクトリ

fTyp = [("画像ファイル", "*.jpg;*.png")]  # 参照ファイルのファイル形式と拡張子


class Control(object):
    def __init__(self, iDir=None):
        # ディレクトリの初期設定
        exist_dir = os.path.exists(dirs_dir)  # ./count/ディレクトリの存在を確認
        if exist_dir is False:
            os.makedirs(dirs_dir, exist_ok=True)  # ない場合は作成

        exist = os.path.exists(dirs)  # ./count/pattern/ディレクトリの存在を確認
        if exist is False:
            os.makedirs(dirs, exist_ok=True)  # ない場合は作成

        exist_re = os.path.exists(result_dirs)  # ./count/result/ディレクトリの存在を確認
        if exist_re is False:
            os.makedirs(result_dirs, exist_ok=True)  # ない場合は作成

        exist_re_xlsx = os.path.exists(excel_dirs)  # ./count/report/ディレクトリの存在を確認
        if exist_re_xlsx is False:
            os.makedirs(excel_dirs, exist_ok=True)  # 無い場合は作成

        exist_setting_dir = os.path.exists(setting_dir)  # ./count/setting/ディレクトリの存在を確認
        if exist_setting_dir is False:
            os.makedirs(setting_dir, exist_ok=True)  # 無い場合は作成
        self.setting_dir = setting_dir

        self.iDir = excel_dirs

        self.check_result_dir_day_exists()

        self.db = DatabaseManage(db_file)  # データベースを扱うための
        self.main_win = None
        self.test = False
        response = self.db.select_row("product", False, "product_name")  # データベース上に製品情報が登録されているか確認
        self.matching_threshold = 0.85
        self.erode = 5
        self.dilate = 3
        self.thresh_area = 100
        self.yield_rate_limit = 80
        self.hls_range = HLSRange()
        # 製品情報がない場合は、初期設定として、comboboxに"製品情報を登録してください"のメッセージを表示
        if not response[0][1]:
            self.product_names = []
            self.product_names.append("製品情報を登録してください")
        else:
            self.product_names = response[0][1]  # 製品情報がある場合は製品名のリストを返す

        self.main_window = None
        self.test = False
        self.label_html_writer = LabelHTMLWriter()
        self.qr_code_generator = QRCodeBase64Generator()

    def set_hls_range(self, h_range_width, l_range_width, s_range_width):
        """
        get_hls_maskに設定値を反映する
        """
        self.hls_range.set_range_width(h_range_width, l_range_width, s_range_width)

    def get_hls_range(self):
        return self.hls_range.get_range_width()

    def check_result_dir_day_exists(self):
        """
        日付フォルダがあるかどうか確認し、なければ作成する
        :return:
        """
        today = datetime.now()  # 時刻の取得
        today_str = "{0:%Y%m%d}".format(today)
        self.result_dir_day = result_dirs + today_str + "/"  # 本日の日付のディレクトリの存在を確認
        exist_day = os.path.exists(self.result_dir_day)
        if exist_day is False:
            os.makedirs(self.result_dir_day, exist_ok=True)  # ない場合は作成

    def change_setting(self, product_name):
        setting_file = setting_dir + product_name + ".pkl"
        if os.path.exists(setting_file) is True:
            settings = load_setting_file(setting_dir, product_name)
            self.matching_threshold, self.erode, self.dilate, self.thresh_area, \
                h_range, l_range, s_range = settings
        else:
            self.matching_threshold = 0.85
            self.erode = 5
            self.dilate = 3
            self.thresh_area = 100
            h_range = 30
            l_range = 30
            s_range = 30
        self.set_hls_range(h_range, l_range, s_range)  # 設定が変更されたら変更する

    def file_open(self, parent, preprocess):
        """
        ダイアログからファイルを呼び出して、画像の配列を返す
        :param parent: ファイル参照する親ウィンドウ parentを指定しなかった場合、ダイアログを呼び出すと、rootウィンドウが上にくる
        :param preprocess: 呼び出した画像に前処理をするかどうか
        :return: 呼び出した画像の配列
        """
        filename = tkfd.askopenfilename(filetypes=fTyp, initialdir=self.iDir, parent=parent)
        # ファイル名に日本語が含まれている場合を考慮して、デコードして画像を読み込む
        n_name = np.fromfile(filename, np.uint8)
        frame = cv2.imdecode(n_name, cv2.IMREAD_COLOR)
        # 初期設定のディレクトリを開いたディレクトリで上書きする
        self.iDir = os.path.dirname(filename)
        if preprocess == 1:  # 前処理をする場合
            pre = Preprocess(frame.shape[1], frame.shape[0])
            frame = pre.preprocessing(frame, 500, 500)
        return frame

    def start_regi(self):
        """
        データベースから製品名を取り出して、リスト→タプル化
        :return: 製品名リストをタプルに変換したもの
        """
        response = self.db.select_row("product", False, "product_name")  # データベースから製品名を取得
        self.product_names = response[0][1]  # 製品名のリスト
        product_names_t = tuple(self.product_names)  # リストをタプルに変換
        return product_names_t

    def product_bind(self, product_name):
        """
        製品名を使用して、データベースから製品の情報を取り出す
        :param product_name: 製品名
        :return: figure_no, theoretical_amount, imgtk
        """
        # データベースから製品の情報を取得
        response = self.db.select_row("product", False, "figure_No", "theoretical_amount", "dir_name",
                                      "yield_rate_limit", product_name=product_name)
        if not response[0][1]:
            # 製品情報がない場合
            figure_no = ""
            theoretical_amount = ""
            yield_rate_limit = ""
            imgtk = None
            return figure_no, theoretical_amount, yield_rate_limit, imgtk
        else:
            # 製品情報がある場合
            figure_no = response[0][1][0]
            theoretical_amount = response[1][1][0]
            yield_rate_limit = response[3][1][0]
            pattern_dir = response[2][1][0]
            pattern_n = pattern_dir + "pattern1.jpg"
            # ファイル名に日本語が含まれている場合を考慮して、デコードして画像を読み込む
            n_name = np.fromfile(pattern_n, np.uint8)
            img = cv2.imdecode(n_name, cv2.IMREAD_COLOR)
            height, width = img.shape[:2]
            # 横長のパターンを読み込む
            if height > width:  # pattern1.jpgが縦長だった場合
                pattern_n = pattern_dir + "pattern2.jpg"  # 90°回転したpatten2.jpgは横長
                # ファイル名に日本語が含まれている場合を考慮して、デコードして画像を読み込む
                n_name = np.fromfile(pattern_n, np.uint8)
                img = cv2.imdecode(n_name, cv2.IMREAD_COLOR)
                height, width = img.shape[:2]
            # 高さ40px固定で縦横比を崩さないようにリサイズする
            width = width * 40 / height
            height = 40
            # 画像が枠の外にはみ出ないように変更
            if width > 180:
                height *= 180 / width
                width = 180
            img2 = cv2.resize(img, (int(width), int(height)))  # resizeはint型しか受け付けないのでintとする。画像のリサイズ
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)  # tkinter上に貼り付けるためPIL方式に変換
            img2 = Image.fromarray(img2)  # Imageオブジェクトへの変換
            imgtk = ImageTk.PhotoImage(image=img2)  # tkinterで扱える形に変換
            return figure_no, theoretical_amount, yield_rate_limit, imgtk

    def count(self, num, product_name, control_no, sheet_no, dialog, cap, frame, matching_threshold=None,
              h_range=None, l_range=None, s_range=None,
              erode_size=None, dilate_size=None, thresh_area=None):
        """
        :param num: 手法を決める数値
        :param product_name: str
        :param control_no: str
        :param sheet_no: str
        :param dialog: True or False
        :param cap: dfk4tk.VideoCapture4DFK()
        :param frame: カウントする画像
        :param matching_threshold: パターンマッチングの閾値
        :param h_range: Hチャンネルの色の範囲の幅
        :param l_range: Lチャンネルの色の範囲の幅
        :param s_range: Sチャンネルの色の範囲の幅
        :param erode_size: 収縮量
        :param dilate_size: 膨張量
        :param thresh_area: 除外面積
        :return: result または エラーがある場合False,None
        """
        # 製品情報の取得
        response = self.db.select_row("product", False, "marking", "figure_No", "theoretical_amount", "dir_name",
                                      "yield_rate_limit", product_name=product_name)
        if not response[0][1]:  # 製品情報がない場合
            return None
        else:
            # 製品情報がある場合
            self.check_result_dir_day_exists()  # 日付が変わっていたら、新しい日付フォルダを作成する
            product_dir_name = self.result_dir_day + product_name + "/"
            exist_product_dir = os.path.exists(product_dir_name)
            if exist_product_dir is False:
                os.makedirs(product_dir_name, exist_ok=True)
            self.figure_no = response[1][1][0]
            self.theoretical_amount = response[2][1][0]
            self.yield_rate_limit = response[4][1][0]
            pattern_dir = response[3][1][0]
            dirs_name = product_dir_name + control_no + "/"
            dirs_exist = os.path.exists(dirs_name)  # 管理Noのついたファイルがあるかどうか確認
            if dirs_exist is False:
                os.makedirs(dirs_name, exist_ok=True)  # ない場合作成
            dir_name = dirs_name + sheet_no + "/"
            # この管理No, シートNoを持つ製品が過去に存在しないかどうか確認する
            response = self.db.select_row("result", True, control_No=control_no, sheet_No=sheet_no)
            if not response[0][1]:  # 存在しない場合 response = [("marking", []), ("figureNo", []),...]となっているはず
                os.makedirs(dir_name, exist_ok=True)
                path = dir_name + "frame.jpg"
                # 画像を撮影した場合
                if dialog is False:
                    img1 = cap.set_exp_and_get_image(-4)  # 露光の高い画像を取得
                    path1 = dir_name + "exp-4.jpg"
                    ext = os.path.splitext(path1)[1]  # 日本語を含むファイル名を扱う
                    result_encode, n = cv2.imencode(ext, img1)  # 画像をエンコード
                    with open(path1, mode='w+b') as f:
                        n.tofile(f)  # 撮影画像の保存
                    img2 = cap.set_exp_and_get_image(-5)  # 露光の低い画像を取得
                    path2 = dir_name + "exp-5.jpg"
                    ext = os.path.splitext(path2)[1]  # 日本語を含むファイル名を扱う
                    result_encode, n = cv2.imencode(ext, img2)  # 画像をエンコード
                    with open(path2, mode='w+b') as f:
                        n.tofile(f)  # 撮影画像の保存
                    frame = cap.get_hdr(img1, img2)  # HDRを使用して画像を合成
                ext = os.path.splitext(path)[1]  # 日本語を含むファイル名を扱う
                result_encode, n = cv2.imencode(ext, frame)  # 画像をエンコード
                with open(path, mode='w+b') as f:
                    n.tofile(f)  # 撮影画像の保存
                # 保存した画像を呼び出してからカウント開始する
                n = np.fromfile(path, dtype=np.uint8)
                frame = cv2.imdecode(n, cv2.IMREAD_COLOR)
                if num == 0:
                    pre = Preprocess(frame.shape[1], frame.shape[0])
                    img_rot = pre.preprocessing(frame, 500, 500)  # 射影変換などの前処理
                    pat = PatternImage(15, self.matching_threshold)
                    # パターンマッチング
                    if matching_threshold is None:
                        result, is_count, _, _, _, _, _ = pat.get_result_and_count(img_rot, pattern_dir, self.matching_threshold, self.hls_range)
                    else:
                        result, is_count, _, _, _, _, _ = pat.get_result_and_count(img_rot, pattern_dir, matching_threshold, self.hls_range)
                else:
                    binary = pickle.dumps(frame)
                    pickle_copy = pickle.loads(binary)
                    if erode_size is None:
                        result, is_count = count_contours(pickle_copy, self.erode, self.dilate, self.thresh_area)
                    else:
                        result, is_count = count_contours(pickle_copy, erode_size, dilate_size, thresh_area)
                img_draw = result
                # 結果画像の保存
                path = dir_name + "result.jpg"
                ext = os.path.splitext(path)[1]  # 日本語を含むファイル名を扱う
                result_encode, n = cv2.imencode(ext, img_draw)  # ファイル名のエンコード
                with open(path, mode='w+b') as f:
                    n.tofile(f)  # 結果画像の保存
                self.product_name = product_name
                self.control_no = control_no
                self.sheet_no = sheet_no
                result = (dir_name, self.figure_no, self.product_name, self.control_no, self.sheet_no,
                          self.theoretical_amount, self.yield_rate_limit, is_count, img_draw)
                self.test = True
                return result
            # 既に存在している場合、エラーを返す
            else:
                return False

    def save_result(self, dir_name, worker_name, str_now, figure_no, product_name, control_no, sheet_no,
                    theoretical_amount, is_count, correct_count, false_detection, not_detected,
                    new_control_no, new_sheet_no):
        try:
            # カウントボタンを押したときと、管理Noが変わった場合
            if new_control_no != control_no:
                control_no = new_control_no  # 変更後の管理Noを管理Noとする
                product_dir_name = self.result_dir_day + product_name + "/"
                dirs_name = product_dir_name + control_no + "/"
                dirs_exist = os.path.exists(dirs_name)  # 管理Noのついたファイルがあるかどうか確認
                if dirs_exist is False:
                    os.makedirs(dirs_name, exist_ok=True)  # ない場合作成
                new_dir_name = dirs_name + sheet_no + "/"
                os.rename(dir_name, new_dir_name)
                dir_name = new_dir_name  # 変更後のディレクトリ名をディレクトリ名とする

            if new_sheet_no != sheet_no:
                sheet_no = new_sheet_no  # 変更後のシートNoをシートNoとする
                product_dir_name = self.result_dir_day + product_name + "/"
                dirs_name = product_dir_name + control_no + "/"
                new_dir_name = dirs_name + sheet_no + "/"
                os.rename(dir_name, new_dir_name)
                dir_name = new_dir_name
            csv_name = dir_name + "result.csv"
            if is_count > theoretical_amount:
                count_error = 1
            else:
                count_error = 0
            # CSVファイルの作成
            make_csv_file(csv_name,
                          worker_name=worker_name,
                          date=str_now,
                          file_dir=dir_name,
                          figure_No=figure_no,
                          product_name=product_name,
                          control_No=control_no,
                          sheet_No=sheet_no,
                          theoretical_amount=theoretical_amount,
                          good_count=is_count,
                          correct_count=correct_count,
                          false_detection=false_detection,
                          not_detected=not_detected,
                          count_error=count_error
                          )
            # SQLのresultテーブルに結果を記入
            self.db.write_row("result",
                              ("worker_name", worker_name),
                              ("date", str_now),
                              ("file_dir", dir_name),
                              ("figure_No", figure_no),
                              ("product_name", product_name),
                              ("control_No", control_no),
                              ("sheet_No", sheet_no),
                              ("theoretical_amount", theoretical_amount),
                              ("good_count", is_count),
                              ("marking_count", 0),
                              ("no_piece", 0),
                              ("correct_count", correct_count),
                              ("false_detection", false_detection),
                              ("not_detected", not_detected),
                              ("count_error", count_error)
                              )
            return True
        # 存在しているファイルに名前を変更しようとした場合
        except FileExistsError:
            return False

    def delete_dir(self, product_name, control_no, sheet_no):
        """
        エラーによって、検出が止まってしまった場合の
        作成したディレクトリの削除
        """
        dir_name = self.result_dir_day + product_name + "/" + control_no + "/" + sheet_no + "/"
        shutil.rmtree(dir_name)

    def open_result(self, control_no, sheet_no, product_name):
        """
        保存された結果を呼び出して、結果数値と画像を返す
        :return: result または False
        """
        # 結果の参照
        response = self.db.select_row("result", False, "file_dir", "good_count", "correct_count", "false_detection",
                                      "not_detected", "date", "theoretical_amount",
                                      product_name=product_name, control_No=control_no, sheet_No=sheet_no)
        # 結果が存在しない場合
        if not response[0][1]:
            return False
        else:
            # 存在する場合
            dir_name = response[0][1][0]
            is_count = response[1][1][0]
            correct_count = response[2][1][0]
            false_detection = response[3][1][0]
            not_detected = response[4][1][0]
            date = response[5][1][0]
            theoretical_amount = response[6][1][0]
            path = dir_name + "result.jpg"
            n = np.fromfile(path, dtype=np.uint8)  # 日本語を含むファイルを扱う
            img_draw = cv2.imdecode(n, cv2.IMREAD_COLOR)  # ファイルのデコード
            result = (is_count, correct_count, false_detection, not_detected, dir_name, img_draw,
                      date, theoretical_amount)
            return result

    def update_prev(self, date, control_no, sheet_no, correct_count, false_detection, not_detected):
        """
        dateによって定められた1行のfile_dirからディレクトリに結果を移動する
        データベースのcontrol_No, sheet_No, file_dirを変更する
        :return: True またはエラーの場合None, False
        """
        try:
            # 結果の参照
            response = self.db.select_row("result", False, "file_dir", "correct_count", "false_detection",
                                          "not_detected", date=date)
            dir_name = response[0][1][0]  # 結果から情報を取り出す ここでもエラーになる可能性がある-->Exception
            for i in range(3):
                if i == 0:
                    split_path, ext = os.path.split(dir_name)
                else:
                    split_path, ext = os.path.split(split_path)
            new_dir_names = split_path + "/" + control_no + "/"
            dir_exist = os.path.exists(new_dir_names)
            # 新しい管理Noのディレクトリがあるかどうか確認
            if dir_exist is False:
                os.makedirs(new_dir_names, exist_ok=True)  # ない場合作成
            new_dir_name = new_dir_names + sheet_no + "/"
            # 保存先ディレクトリ名を変更する
            if dir_name != new_dir_name:
                os.rename(dir_name, new_dir_name)  # ファイルのリネーム ここでエラーになる可能性がある-->FileExistError
            self.db.update_row("result", ("file_dir", new_dir_name), ("control_No", control_no),
                               ("sheet_No", sheet_no), ("correct_count", correct_count),
                               ("false_detection", false_detection), ("not_detected", not_detected), date=date)
            return True
        # ファイルが既に存在している場合、エラーを返す
        except FileExistsError:
            return None
        # 結果情報がない場合
        except Exception:
            return False

    def delete_prev(self, date):
        """
        dateによって定められた1行を削除する
        またその結果が保存されているディレクトリも削除する
        :return: True　またはエラーの場合False
        """
        response = self.db.select_row("result", False, "file_dir", date=date)  # 結果の参照
        dir_name = response[0][1][0]
        try:
            shutil.rmtree(dir_name)  # ディレクトリごと削除
            self.db.delete_row("result", date=date)  # データベースからも結果情報の削除する
            return True
        except Exception:
            return False

    def shutter(self, cap, frame, dialog):
        """
        dialog=Falseの場合、画像処理画像を2回撮影してHDR画像を作成。前処理を行って上下左右反転した画像を返す。
        dialog=Trueの場合、前処理のみを行った画像を返す。
        :param cap: dfk4tk.VideoCapture4dFK()
        :param frame: dialog=Trueの場合に使用
        :param dialog: True or False
        :return: 処理後の画像の配列
        """
        # 撮影ボタンが押された場合
        if dialog is False:
            img1 = cap.set_exp_and_get_image(-4)  # 露光の高い画像を取得
            img2 = cap.set_exp_and_get_image(-5)  # 露光の低い画像を取得
            frame = cap.get_hdr(img1, img2)  # HDR画像を作成
        file_name = "_.jpg"
        ext = os.path.splitext(file_name)[1]  # 日本語を含むファイル名を扱う
        result_encode, n = cv2.imencode(ext, frame)  # 画像をエンコード
        with open(file_name, mode='w+b') as f:
            n.tofile(f)  # 撮影画像の保存
        n = np.fromfile(file_name, dtype=np.uint8)
        frame = cv2.imdecode(n, cv2.IMREAD_COLOR)
        pre = Preprocess(frame.shape[1], frame.shape[0])
        frame2 = pre.preprocessing(frame, 500, 500)  # 前処理した画像の取得
        if dialog is False:
            frame2 = cv2.flip(frame2, -1)  # 画像の180°回転
        os.remove(file_name)
        return frame2

    def enlarge_img(self, width, height, x_down, y_down, margin_x, margin_y, frame):
        """
        表示画像の拡大
        :param width: 表示画像の横幅
        :param height: 表示画像の高さ
        :param x_down: 拡大の中心点のx座標
        :param y_down: 拡大の中心点のy座標
        :param margin_x: 表示画像を縮小して白画像に貼り付けたときに生じたx軸方向の余白
        :param margin_y: 表示画像を縮小して白画像に貼り付けたときに生じたy軸方向の余白
        :param frame: 拡大する画像の元画像
        :return: 拡大した画像の配列
        """
        img_height, img_width = frame.shape[:2]
        # 余白を取り除いた真の画像のサイズで計算する
        w_magnif = img_width / (width - margin_x * 2)
        h_magnif = img_height / (height - margin_y * 2)
        # 切り取った画像の中心となる地点を計算
        cx = (x_down - margin_x) * w_magnif
        cy = (y_down - margin_y) * h_magnif
        # 切り取る区画の左上、右下座標の取得
        x1 = cx - (width / 2)
        x2 = cx + (width / 2)
        y1 = cy - (height / 2)
        y2 = cy + (height / 2)
        # 切り取る区画が画像範囲を超えている場合
        if x1 < 0:
            x1 = 0
            x2 = width
        if x2 > img_width:
            x2 = img_width
            x1 = img_width - width
        if y1 < 0:
            y1 = 0
            y2 = height
        if y2 > img_height:
            y2 = img_height
            y1 = img_height - height
        frame1 = frame[int(y1):int(y2), int(x1):int(x2)]
        return frame1, x1, y1

    def select_img(self, width, height, x_down, y_down, x_up, y_up, margin_x, margin_y, enlarge, frame,
                   large_x=0, large_y=0):
        """
        パターン画像の選択
        表示画像が拡大しているかどうかによって、パターンの取り方を分岐
        パターンとパターンを含む200x200pxの画像を作成するための数値を計算
        :param width: 表示画像の横幅
        :param height: 表示画像の高さ
        :param x_down: クリック開始地点のx座標
        :param y_down: クリック開始地点のy座標
        :param x_up: ボタンを離した地点のx座標
        :param y_up: ボタンを離した地点のy座標
        :param margin_x: 表示画像を縮小して白画像に貼り付けたときに生じたx軸方向の余白
        :param margin_y: 表示画像を縮小して白画像に貼り付けたときに生じたy軸方向の余白
        :param enlarge: 拡大しているかどうか on(拡大なし) 又は off(拡大あり)
        :param frame: パターンを切り抜くための元画像
        :param large_x: 元画像の拡大後の左上x座標
        :param large_y: 元画像の拡大後の左上y座標
        :return:
        """
        # 拡大されていない場合
        if enlarge == "on":
            img_height, img_width = frame.shape[:2]
            # 元画像と表示画像のサイズ比からクリックされた点の元画像上での位置を算出
            w_magnif = img_width / (width - margin_x * 2)
            h_magnif = img_height / (height - margin_y * 2)
            x_down = (x_down - margin_x) * w_magnif
            y_down = (y_down - margin_y) * h_magnif
            x_up = (x_up - margin_x) * w_magnif
            y_up = (y_up - margin_y) * h_magnif
            x_down = int(x_down)
            y_down = int(y_down)
            x_up = int(x_up)
            y_up = int(y_up)
        # 拡大されている場合
        else:
            # トリミングの左上座標分だけズレているので位置を修正
            x_down += int(large_x)
            x_up += int(large_x)
            y_down += int(large_y)
            y_up += int(large_y)

        # パターンの中心座標を求める
        pattern_cx = int((x_down + x_up) / 2)
        pattern_cy = int((y_down + y_up) / 2)
        result = (x_down, x_up, y_down, y_up, pattern_cx, pattern_cy)
        return result

    def get_info(self, product_name):
        """
        データベースのproductテーブルから製品名でその他の情報を呼び出す
        :return: result またはエラーの場合False
        """
        # 製品情報の取得
        response = self.db.select_row("product", False, "figure_No", "theoretical_amount", "marking",
                                      "yield_rate_limit", product_name=product_name)
        if not response[0][1]:
            return False  # 製品情報の登録がない場合
        else:
            figure_no = response[0][1][0]
            theoretical_amount = response[1][1][0]
            marking = response[2][1][0]
            yield_rate_limit = response[3][1][0]
            result = (figure_no, theoretical_amount, marking, yield_rate_limit)
            return result

    def pattern_change(self, product_name, pattern):
        """
        パターン画像の変更時に使用
        ディレクトリはそのままで、中身の画像のみを更新
        90°ずつ回転した画像を保存
        :param product_name: 製品名
        :param pattern: パターン画像として保存する画像の配列
        """
        # 製品情報の取得
        response = self.db.select_row("product", False, "dir_name", product_name=product_name)
        dir_name = response[0][1][0]
        # パターン名
        pattern_name = dir_name + "pattern1.jpg"
        ext = os.path.splitext(pattern_name)[1]  # 日本語を含むファイル名を扱う
        result_encode, n = cv2.imencode(ext, pattern)  # 画像をエンコード
        with open(pattern_name, mode='w+b') as f:
            n.tofile(f)  # 撮影画像の保存
        # 90°ずつ回転したものを保存 パターンは4枚で1セットとなる
        for i in range(3):
            pattern = pattern.transpose(1, 0, 2)  # 軸の順番を入れ替える
            pattern = pattern[:, ::-1]  # 順番の変更により反転している部分を直す
            file_name = dir_name + "pattern{}.jpg".format(i + 2)
            ext = os.path.splitext(file_name)[1]  # 日本語を含むファイル名を扱う
            result_encode, n = cv2.imencode(ext, pattern)  # 画像をエンコード
            with open(file_name, mode='w+b') as f:
                n.tofile(f)  # 撮影画像の保存

    def save(self, figure_no, product_name, theoretical_amount, yield_rate_limit, marking, pattern):
        """
        入力された情報からproductテーブルに情報を入力
        結果保存用のディレクトリの作成
        パターン画像の保存(90°回転ごとに保存して計4枚)
        :param figure_no: str
        :param product_name: str
        :param theoretical_amount: str
        :param yield_rate_limit: float
        :param marking: 0 or 1
        :param pattern: 画像の配列
        :return:　製品名のリスト またはエラーの場合False, None, 100
        """
        # パターン保存用のディレクトリ作成
        dir_name = "./count/pattern/{0}/".format(product_name)
        os.makedirs(dir_name, exist_ok=True)
        pattern_name = dir_name + "pattern1.jpg"
        try:
            ext = os.path.splitext(pattern_name)[1]  # 日本語を含むファイル名を扱う
            result_encode, n = cv2.imencode(ext, pattern)  # 画像をエンコード
            with open(pattern_name, mode='w+b') as f:
                n.tofile(f)  # 撮影画像の保存
            # 90°ずつ回転して計4枚のパターンを保存する
            for i in range(3):
                pattern = pattern.transpose(1, 0, 2)  # 軸の順番を入れ替える
                pattern = pattern[:, ::-1]  # 順番の変更により反転している部分を直す
                file_name = dir_name + "pattern{}.jpg".format(i + 2)
                ext = os.path.splitext(file_name)[1]  # 日本語を含むファイル名を扱う
                result_encode, n = cv2.imencode(ext, pattern)  # 画像をエンコード
                with open(file_name, mode='w+b') as f:
                    n.tofile(f)  # 撮影画像の保存
            # データベースへの書き込み
            self.db.write_row("product",
                              ("figure_No", figure_no),
                              ("product_name", product_name),
                              ("theoretical_amount", int(theoretical_amount)),
                              ("yield_rate_limit", yield_rate_limit),
                              ("marking", marking),
                              ("dir_name", dir_name)
                              )
        except NameError:  # pattern=Noneの場合
            shutil.rmtree(dir_name)
            return False
        except ValueError:  # theoretical_amountがintにならない場合
            shutil.rmtree(dir_name)
            return None
        except Exception:
            shutil.rmtree(dir_name)
            return 100
        else:
            response = self.db.select_row("product", False, "product_name")  # productテーブルからproduct_nameを取得
            return response[0][1]

    def output_filename(self, parent):
        """
        選択したファイル名を返す
        :param parent: 呼び出したウィンドウ
        :return:
        """
        fTyp = [("HTMLファイル", "*.html")]  # 参照ファイルのファイル形式と拡張子
        filename = tkfd.asksaveasfilename(filetypes=fTyp, initialdir=self.iDir, parent=parent)
        self.iDir = os.path.dirname(filename)
        # 拡張子ついていなければ、xlsxをつける
        if filename[-5:] == ".html":
            return filename
        elif "." in filename:
            return False
        elif filename == "":
            return filename
        else:
            filename += ".html"
            return filename

    def get_db(self, control_no):
        """
        管理Noを使用してデータベースから結果を受け取る
        :param control_no: 管理No
        :return: 製品図番、製品名、作業者名、カウント結果 or 結果がない場合False
        """
        try:
            db_result = self.db.select_row("result", False, "figure_No", "date", "worker_name",
                                           "sheet_No", "correct_count",
                                           control_No=control_no)
            figure_no = db_result[0][1][0]
            date = db_result[1][1][0]
            date = date[:10]
            name = db_result[2][1][0]
            sheet_no_list = db_result[3][1]
            correct_count_list = db_result[4][1]
            result_list = []
            for i in range(len(sheet_no_list)):
                try:
                    sheet_no = sheet_no_list[i]
                    sheet_no_num = sheet_no[1:]
                    # 数字以外の文字をハイフンに置き換える int("1_2")---->12となることを防止
                    sheet_no_num = re.sub("\D", "-", sheet_no_num)
                    sheet_no_num = int(sheet_no_num)
                    result = (sheet_no_num, correct_count_list[i])
                    result_list.append(result)
                # 数字ではないシート名の場合は無視する(ex) 上1_1 )
                except ValueError:
                    pass
            result = (figure_no, date, name, result_list)
            return result
        # 管理Noに対する結果が存在しない場合
        except IndexError:
            return False

    def output(self, control, lot_No, save_name):
        """
        管理Noでデータベースを呼び出して結果をエクセルに書き込んで保存する
        :param control: エクセルファイル左側に書き込む管理No
        :param lot_No: Lot No
        :param save_name: 保存するエクセルファイル名
        :return: 管理No1のミス 1
                 正しく保存された場合 10
        """
        # 管理No1, 2両方が入力されたとき
        result = self.get_db(control)
        if result is False:  # 管理No1の結果が存在しなかった場合
            return 1
        else:  # どちらの結果も存在する場合
            figure_no, date, name, result_list = result
            output_html(date, figure_no, lot_No, name, control, result_list, save_name)
            return 10

    def output_sheet_result(self, product_name, control_no, sheet_no, count, worker_name, date):
        """
        シートごとの結果をHTMLファイルに書き出して保存し、WEBブラウザで開く。
        Args:
            product_name(str):
            control_no(str):
            sheet_no(str):
            count(int):
            worker_name(str):
            date(str): YYYY/M/D
        """
        response = self.db.select_row("product", False, "theoretical_amount", product_name=product_name)
        theoretical_amount = response[0][1][0]
        # 歩留まり率は小数点第一位に
        yield_rate = count / theoretical_amount * 100
        yield_rate_decimal = Decimal(yield_rate)
        yield_rate_decimal = yield_rate_decimal.quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)
        yield_rate_str = str(yield_rate_decimal)
        # QRコードの作成
        base64_1 = self.qr_code_generator.generate(f"{control_no}-{sheet_no}")  # 管理番号-シート番号 のQRコード
        base64_2 = self.qr_code_generator.generate(f"{count}")  # 計数結果 のQRコード

        # HTML化
        html_string = self.label_html_writer.generate(product_name, control_no, sheet_no, str(count),
                                                      yield_rate_str, worker_name, date, base64_1, base64_2)

        output_dir = excel_dirs
        # ファイル名に使用不可な文字がないか確認
        _control_no = translate_word.translate_word(control_no, not_available=True)
        _sheet_no = translate_word.translate_word(sheet_no, not_available=True)
        filename = f"{_control_no}-{_sheet_no}.html"
        output_filename = os.path.join(output_dir, filename)
        self.label_html_writer.save(html_string, output_filename)  # ファイル保存
        # WEBブラウザで立ち上げる
        webbrowser.open(os.path.abspath(output_filename))
