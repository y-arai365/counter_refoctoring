import os
import xml.etree.ElementTree as Et

from tisgrabber import TIS_CAM


def load_config(cam, config_path):
    """
    設定ファイルを読み込み、DFK33UJ003カメラの設定を行う
    :param cam: TIS_CAMオブジェクト
    :param config_path: カメラ設定ファイルの場所(.xml)
    """
    if os.path.isfile(config_path):
        device = cam.GetDevices()[0].decode()
        model_name, *_ = device.rsplit(" ", maxsplit=1)

        writer = XMLWriter(config_path)
        device_elem = writer.find_sub_element(writer.root, "device")

        # カメラと設定ファイルで型番が一致しない場合
        if model_name != writer.get_attribute_value(device_elem, "name"):
            return

        # 設定ファイルに書かれているシリアル番号をカメラから取得した番号に書き換える
        writer.replace_attribute_value(device_elem, "unique_name", device)
        writer.write(config_path)

        cam.LoadDeviceStateFromFile(config_path)


class XMLWriter:
    def __init__(self, xml_path):
        """
        xmlの中身を、階層を下りながら確認。値を書き換え、保存する。
        :param xml_path: str XMLファイルのパス
        """
        self.tree = Et.parse(xml_path)
        self.root = self.tree.getroot()

    @staticmethod
    def get_sub_element_tag_list(element):
        """
        一個したの階層の要素名一覧を得る
        :param element: xml.etree.ElementTree.Element
        :return: list[str, ]
        """
        return [e.tag for e in element.getchildren()]

    @staticmethod
    def get_attribute_names(element):
        """
        その要素が持っている属性の名前一覧を得る
        :param element: xml.etree.ElementTree.Element
        :return: list[str, ]
        """
        return list(element.attrib.keys())

    @staticmethod
    def get_element_value(element):
        """
        その要素の値を得る
        :param element: xml.etree.ElementTree.Element
        :return: str
        """
        return element.text

    @staticmethod
    def get_attribute_value(element, attribute_name):
        """
        その要素が持つ属性の値を得る
        :param element: xml.etree.ElementTree.Element
        :param attribute_name: str
        :return: str
        """
        return element.attrib[attribute_name]

    @staticmethod
    def find_sub_element(element, tag_name):
        """
        その要素のひとつ下の階層から、指定した要素名と一致する要素を得る
        :param element: xml.etree.ElementTree.Element
        :param tag_name str
        :return: xml.etree.ElementTree.Element
        """
        return element.find(tag_name)

    @staticmethod
    def replace_attribute_value(element, attribute_name, value):
        """
        その要素が持つ属性の値を書き換える。
        :param element: xml.etree.ElementTree.Element
        :param attribute_name str
        :param value str
        """
        element.attrib[attribute_name] = value

    @staticmethod
    def replace_element_text(element, text):
        """
        その要素の値を書き換える。
        :param element: xml.etree.ElementTree.Element
        :param text str
        """
        element.text = text

    def write(self, xml_path):
        """保存"""
        self.tree.write(xml_path)


if __name__ == '__main__':
    config_path_ = "./camera_config.xml"

    cam_ = TIS_CAM()
    devices = cam_.GetDevices()
    if devices:
        device_ = devices[0].decode()
        cam_.open(device_)

    load_config(cam_, config_path_)

    import cv2
    cap = cv2.VideoCapture(1)

    cap.set(3, 3856)
    cap.set(4, 2764)
    cap.set(6, cv2.VideoWriter_fourcc(*"YUY2"))
    cap.set(37, 0)

    cv2.namedWindow("cap", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("cap", 1200, 900)
    while True:
        ret, frame = cap.read()
        cv2.imshow("cap", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
    print(frame.shape)
    cap.release()
    cv2.destroyAllWindows()
