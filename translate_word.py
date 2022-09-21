"""
translate_wordを呼び出せば、文字の変更を行ってくれる
"""


def number_translate(word, boolean):
    """
    全角数字を半角に直す
    """
    if boolean is True:
        # word.translate(str.maketrans("１", "1"))
        word = word.translate(str.maketrans(u"０１２３４５６７８９．", u"0123456789."))
    return word


def not_available_word_file_translate(word, boolean):
    """
    ファイル保存時に利用できない文字を変換する
    """
    if boolean is True:
        word = word.translate(str.maketrans(u'\/:*?"<>|', u"□□□□□□□□□"))
    return word


def upper_translate(word, boolean):
    """
    全角大文字英字を半角に直す
    """
    if boolean is True:
        word = word.translate(str.maketrans(u"ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
                                            u"ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    return word


def lower_translate(word, boolean):
    """
    全角小文字英字を半角に直す
    """
    if boolean is True:
        word = word.translate(str.maketrans(u"ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
                                            u"abcdefghijklmnopqrstuvwxyz"))
    return word


def translate_word(word, number=False, not_available=False,
                   upper=False, lower=False, upper_lower=False, lower_upper=False):
    """
    文字列の主に全角半角を変更する関数
    :param word: 変更したいstr型 str型でない場合は、wordをそのまま返す
    :param number: 数字の全角半角を変更する
    :param not_available: ファイル名に使用できない文字を変更する
    :param upper: 大文字英字の全角半角を変更する
    :param lower: 小文字英字の全角半角を変更する
    :param upper_lower: 英字すべてを小文字にする
    :param lower_upper: 英字すべてを大文字にする
    :return:
    """
    if type(word) == str:
        word = number_translate(word, number)
        word = not_available_word_file_translate(word, not_available)
        word = upper_translate(word, upper)
        word = lower_translate(word, lower)
        if upper_lower is True:
            word.lower()
        if lower_upper is True:
            word.upper()
    return word


if __name__ == "__main__":
    words = u"ＡＡＡＡccccc0.0．00１１１１"
    print(words)
    w = translate_word(words, number=True, not_available=True, upper=True, lower=True)
    print(w)
