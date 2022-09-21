import datetime
import os
import re


def output_html(date, figure_No, lot_No, name, control_no, result, save_name):
    """
    template.htmlに情報を入力してsave_nameのHTMLファイルを出力する
    :param date: 日付
    :param figure_No: 製品図番
    :param lot_No: Lot No
    :param control_no: 管理No
    :param name: 作業者名
    :param result: 結果のリスト[[num, count], [num, count], ...]
    :param save_name: 保存名
    :return: 問題なく保存できればTrue エラーがあった場合False
    """
    try:
        # テンプレートとなるhtmlを読み込む
        with open("template.html", mode="r", encoding="utf-8") as html_f:
            read_html = html_f.read()

        counts = 0
        # 基礎情報を入力する
        read_html = read_html.replace("__Date__", date)
        read_html = read_html.replace("__DwgNo__", figure_No)
        read_html = read_html.replace("__LotNo__", lot_No)
        read_html = read_html.replace("__ControlNo__", control_no)
        read_html = read_html.replace("__Name__", name)

        # 現在時刻の入力
        now = datetime.datetime.now()
        str_now = "{0:%m/%d %H:%M}".format(now)
        read_html = read_html.replace("__Time__", str_now)

        max_num = len(result)
        # 結果を書き込む
        for i in range(len(result)):
            num = result[i][0]  # シート番号を取得する
            correct_count = result[i][1]  # カウント数を取得する
            read_html = read_html.replace("__{:02}__".format(num), str(correct_count))  # 数値を置き換える
            counts += correct_count  # 全体合計を取得する

        # シート番号の最大値以降と抜けている番号は空白とする
        pattern = "__\d\d__"
        results = re.findall(pattern, read_html, re.S)
        if results == []:
            pass
        else:
            for pattern_result in results:
                read_html = read_html.replace(pattern_result, "　")

        # シート数
        read_html = read_html.replace("__SheetNum__", str(max_num))

        # 良品合計
        read_html = read_html.replace("__Total__", str(counts))
        with open(save_name, mode="w") as html_f:
            html_f.write(read_html)
        return True
    except:
        import traceback
        traceback.print_exc()
        return False


class LabelHTMLWriter:
    def __init__(self, template_file_path="label_template.html"):
        """
        シートごとに発行するラベル用のHTMLをテンプレートとなるHTML内の文字を置き換えることで作成する。

        Args:
            template_file_path (str):
        """
        with open(template_file_path, mode="r", encoding="utf-8") as f:
            self._template: str = f.read()

    def generate(self, product_name, lot_no, sheet_no, quantity, yield_rate, name, date, base64_1, base64_2):
        """
        シートの情報からhtml形式のテキストを作成する

        Args:
            product_name (str)  : 製品名
            lot_no (str)        : 管理番号
            sheet_no (str)      : シート番号
            quantity (str)      : 計数結果
            yield_rate (str)    : 歩留まり率（計数結果 / 理論数量）
            name (str)          : 作業者名
            date (str)          : 日付
            base64_1 (str)      : Base64形式の"管理番号 - シート番号"が入ったQRコードの画像
            base64_2 (str)      : Base64形式の"計数結果"が入ったQRコードの画像

        Returns:
            str                 : HTML形式のテキスト
        """
        trans_dict = {
            "__ProductName__":  product_name,
            "__LotNo__":        lot_no,
            "__SheetNo__":      sheet_no,
            "__Quantity__":     quantity,
            "__Yield__":        yield_rate,
            "__Name__":         name,
            "__Date__":         date,
            "__Base64Image1__": base64_1,
            "__Base64Image2__": base64_2,
        }

        html_dst = str(self._template)  # self._templateを書き換えないようにコピーを渡す。
        for key, value in trans_dict.items():
            html_dst = html_dst.replace(key, value)
        return html_dst

    @staticmethod
    def save(html_string, file_path):
        """
        生成したhtml文字列を保存する

        Args:
            html_string (str): html形式の文字列
            file_path (str): ファイルパス。"~.html"であること。

        """
        ext = os.path.splitext(file_path)[-1]
        if ext != ".html":
            raise ValueError(f"'.html' file is required but '{ext}' was given.")

        with open(file_path, "w") as html_file:
            html_file.write(html_string)


if __name__ == "__main__":
    from qr_code import QRCodeBase64Generator

    # 管理番号ごとの集計結果
    result = output_html("2019/7/12", "aaaa", "aaaa", "tom", "111", [[1, 1000], [4, 1000]], "name.html")
    print(result)

    # シートごとに発行するラベル
    label_html_save_path = "result.html"

    label_writer = LabelHTMLWriter("label_template.html")
    qr64_gen = QRCodeBase64Generator()

    pn = "123-4567X"
    ln = "abc001"
    sn = "上19"[1:]
    qty = "1301"
    yr = "58.1"
    who = "根本"
    today = datetime.datetime.today().strftime("%Y.%m.%d")

    ln_and_sn_base64 = qr64_gen.generate(ln + "-" + sn)
    qty_base64 = qr64_gen.generate(qty)
    dst_html = label_writer.generate(pn, ln, sn, qty, yr, who, today, ln_and_sn_base64, qty_base64)

    label_writer.save(dst_html, label_html_save_path)
