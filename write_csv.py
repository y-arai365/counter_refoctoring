import csv
import os


def make_csv_file(path, **kargs):
    """
    csvファイルに結果を書き込む
    :param path: 作成するcsvファイルのパス そのファイルが存在する場合、作成されない
    :param kargs: key:csvファイルのヘッダー value:実際の値
    """
    header = []
    for key in kargs:
        header.append(key)
    path_exist = os.path.exists(path)
    if path_exist is False:
        with open(path, "w") as csv_file:
            writer = csv.DictWriter(csv_file, header)
            writer.writeheader()
            writer.writerow(kargs)
    else:
        pass
        # print("この名前をもつcsvファイルは存在しています。")


if __name__ == "__main__":
    file_path = "test.csv"
    make_csv_file(file_path, a=100, b="b", c="hello, world", d=10000)
