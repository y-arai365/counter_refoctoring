import sqlite3


class DatabaseManage(object):
    def __init__(self, filepath):
        """
        :param filepath: データベースファイルのファイルパス
        """
        self.conn = sqlite3.connect(filepath)
        self.cur = self.conn.cursor()
        self.result_header = ["id", "worker_name", "date", "file_dir", "figure_No", "product_name", "control_No",
                              "sheet_No", "theoretical_amount", "good_count", "marking_count", "no_piece",
                              "correct_count", "false_detection", "not_detected", "count_error"]
        self.product_header = ["id", "figure_No", "product_name", "theoretical_amount", "marking", "yield_rate_limit",
                               "dir_name"]
        self.create_table()

    def create_table(self):
        """
        テーブルを作成する関数
        データベースファイル上にテーブルが存在しなければ作成
        作成するテーブルは固定
        """
        self.cur.execute("create table if not exists result(ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                         "worker_name varchar(100),"
                         "date varchar(100),"
                         "file_dir varchar(100),"
                         "figure_No varchar(100),"
                         "product_name varchar(100),"
                         "control_No varchar(100),"
                         "sheet_No varchar(100),"
                         "theoretical_amount INTEGER,"
                         "good_count INTEGER,"
                         "marking_count INTEGER,"
                         "no_piece INTEGER,"
                         "correct_count INTEGER,"
                         "false_detection INTEGER,"
                         "not_detected INTEGER,"
                         "count_error INTEGER);")
        self.conn.commit()
        self.cur.execute("create table if not exists product(ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                         "figure_No varchar(100),"
                         "product_name varchar(100),"
                         "theoretical_amount INTEGER,"
                         "marking INTEGER,"
                         "yield_rate_limit REAL,"
                         "dir_name varchar(100))")
        self.conn.commit()

    def select_row(self, tablename, allcolumn, *args, **kwargs):
        """
        テーブルから特定の情報を取り出す
        :param tablename: 参照したいテーブル名
        :param allcolumn: Trueの場合、参照したいargsなしで、参照した行のすべてのカラムの値を受け取れる True or False
        :param args: 参照する行の取り出したいカラム名 "product_name", "figure_No", ...
        :param kwargs: 参照する行を限定したいときの条件
        :return result: 取り出した情報とそのカラム名をタプル形式で、リストに格納する [(a, [b]), (c, [a, b, c, d])]
        """
        sentence = "SELECT * FROM {}".format(tablename)
        if kwargs != {}:
            kwargs = kwargs.items()
            kwargs = list(kwargs)
            value = kwargs[0][1]
            if type(value) == str:
                conditions = "{0}='{1}'".format(kwargs[0][0], value)
            elif type(value) == int:
                conditions = "{0}={1}".format(kwargs[0][0], value)
            else:
                conditions = ""
            for i in range(len(kwargs) - 1):
                value = kwargs[i + 1][1]
                if type(value) == str:
                    conditions += "and {0}='{1}'".format(kwargs[i+1][0], value)
                elif type(value) == int:
                    conditions += "and {0}={1}".format(kwargs[i+1][0], value)
                else:
                    pass
            sentence += " where {0}".format(conditions)
        self.cur.execute(sentence)
        res = self.cur.fetchall()
        args_index = []
        if allcolumn is True:
            if tablename == "product":
                args = self.product_header
            else:
                args = self.result_header
        if tablename == "product":
            header = self.product_header
        else:
            header = self.result_header
        for arg in args:
            index = header.index(arg)
            args_index.append(index)
        if len(res) == 0:
            result = []
            for i in range(len(args_index)):
                result.append((args[i], []))
        else:
            result = []
            for i in range(len(args_index)):
                res_list = []
                index = args_index[i]
                for row in res:
                    res_list.append(row[index])
                result.append((args[i], res_list))
        return result

    def write_row(self, tablename, *args):
        """
        テーブルに新規の行を書き込む
        :param tablename: 書き込みたいテーブル名
        :param args: そのテーブルのカラム名とその値のタプル 原則id以外のカラム全記入
                     ('worker_name', '鈴木'), ('date','2019-03-12'), ...
        """
        columns = []
        values = []
        for first, second in args:
            columns.append(first)
            values.append(second)

        sentence = f"INSERT INTO {tablename} {tuple(columns)} VALUES {tuple(values)}"
        self.cur.execute(sentence)
        self.conn.commit()

    def delete_row(self, tablename, **kwargs):
        """
        テーブルの条件にひっかかった行を削除する
        :param tablename: 削除したい行を持つテーブル
        :param kwargs: そのテーブルのカラム名とその値　product_name='aaaaaaa'
        """
        if kwargs != {}:
            kwargs = kwargs.items()
            kwargs = list(kwargs)
            value = kwargs[0][1]
            if type(value) == str:
                conditions = "{0}='{1}'".format(kwargs[0][0], value)
            elif type(value) == int:
                conditions = "{0}={1}".format(kwargs[0][0], value)
            else:
                conditions = ""
            for i in range(len(kwargs)-1):
                value = kwargs[i+1][1]
                if type(value) == str:
                    conditions += "and {0}='{1}'".format(kwargs[0][0], value)
                elif type(value) == int:
                    conditions += "and {0}={1}".format(kwargs[0][0], value)
                else:
                    pass
            sentence = "delete from {0} where {1}".format(tablename, conditions)
        else:
            sentence = "delete from {0}".format(tablename)
        self.cur.execute(sentence)
        self.conn.commit()

    def update_row(self, tablename, *args, **kwargs):
        """
        条件にひっかかった行の内容変更
        :param tablename: 上書きしたいテーブル
        :param args: 変更するカラム名とその値のタプル、またはリスト
        :param kwargs: 条件としたいカラム名とその値
        """
        sentence = f"UPDATE {tablename}"

        updates = []
        for first, second in args:
            updates.append(f"{first}={second!r}")
        set_ = " SET " + ", ".join(updates)
        sentence += set_

        if kwargs:
            conditions = []
            for key, value in kwargs.items():
                conditions.append(f"{key}={value!r}")
            where = " WHERE " + " AND ".join(conditions)
            sentence += where

        self.cur.execute(sentence)
        self.conn.commit()

    def close_sql(self):
        self.conn.commit()
        self.cur.close()
        self.conn.close()


if __name__ == '__main__':
    db = DatabaseManage(":memory:")

    # データの書き込み
    db.write_row("product",
                 ("figure_No", "abc"),
                 ("product_name", "ABC"),
                 ("theoretical_amount", 1000),
                 ("marking", 1),
                 ("yield_rate_limit", 10.1),
                 ("dir_name", "directory1")
                 )

    db.write_row("product",
                 ("figure_No", "def"),
                 ("product_name", "DEF"),
                 ("theoretical_amount", 2000),
                 ("marking", 2),
                 ("yield_rate_limit", 20.2),
                 ("dir_name", "directory2")
                 )

    db.write_row("product",
                 ("figure_No", "ghi"),
                 ("product_name", "GHI"),
                 ("theoretical_amount", 3000),
                 ("marking", 3),
                 ("yield_rate_limit", 30.3),
                 ("dir_name", "directory3")
                 )

    db.write_row("product",
                 ("figure_No", "jkl"),
                 ("product_name", "JKL"),
                 ("theoretical_amount", 4000),
                 ("marking", 4),
                 ("yield_rate_limit", 40.4),
                 ("dir_name", "directory4")
                 )

    # テーブル内の全てのデータ
    print('>>> db.select_row("product", True)')
    print(db.select_row("product", True))
    print()

    # 指定したカラムの値のみ取得
    ret = db.select_row("product", False, "product_name")
    products = ret[0][1]
    print(f'>>> db.select_row("product", False, "marking", "figure_No", product_name={products[2]})')
    # 条件に合うデータの内、指定したカラムの値のみ取得
    # 引数の順番で取得できる
    print(db.select_row("product", False, "marking", "figure_No", product_name=products[2]))
    print()

    # データの更新
    print('''>>> db.update_row("product",
                 ("figure_No", "mno"),
                 ("theoretical_amount", 5000),
                 ("marking", 5),
                 ("yield_rate_limit", 50.5), product_name="JKL")''')
    db.update_row("product",
                  ("figure_No", "mno"),
                  ("theoretical_amount", 5000),
                  ("marking", 5),
                  ("yield_rate_limit", 50.5), product_name="JKL")
    print('>>> db.select_row("product", True)')
    print(db.select_row("product", True))
    print()

    # データの削除
    print('>>> db.delete_row("product", product_name="DEF")')
    db.delete_row("product", product_name="DEF")
    print('>>> db.select_row("product", True)')
    print(db.select_row("product", True))

    db.close_sql()
