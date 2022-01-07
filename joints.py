import numpy as np
import mediapipe as mp
import cv2
import math
from enum import IntEnum, auto


class ConnLabel(IntEnum):
    def _generate_next_value_(self, _start, count, _last_values):
        """Generate consecutive automatic numbers starting from zero."""
        return count

    THUMB_CB = auto()
    THUMB_MCB = auto()
    THUMB_PPB = auto()
    THUMB_DPB = auto()
    INDEX_FINGER_CB = auto()
    INDEX_FINGER_MCB = auto()
    INDEX_FINGER_PPB = auto()
    INDEX_FINGER_DPB = auto()
    MIDDLE_FINGER_CB = auto()
    MIDDLE_FINGER_MCB = auto()
    MIDDLE_FINGER_PPB = auto()
    MIDDLE_FINGER_DPB = auto()
    RING_FINGER_CB = auto()
    RING_FINGER_MCB = auto()
    RING_FINGER_PPB = auto()
    RING_FINGER_DPB = auto()
    PINKY_FINGER_CB = auto()
    PINKY_FINGER_MCB = auto()
    PINKY_FINGER_PPB = auto()
    PINKY_FINGER_DPB = auto()


class NormalLabel(IntEnum):
    def _generate_next_value_(self, _start, count, _last_values):
        """Generate consecutive automatic numbers starting from zero."""
        return count

    PALM_NORMAL = auto()
    INDEX_FINGER_MCP_NORMAL = auto()
    MIDDLE_FINGER_MCP_NORMAL = auto()
    RING_FINGER_MCP_NORMAL = auto()
    PINKY_FINGER_MCP_NORMAL = auto()


class joints:
    def __init__(self):
        # Constants
        self.LANDMARK_COUNT = 21
        self.CONNECTION_COUNT = 21
        self.NORMAL_COUNT = 5
        self.COORD_DIM = 3
        self.PLACE_HOLDER = 0

        # Store connection instructions
        # 1) Basic joint angles
        # 2)
        self.CONNECTIONS_PARENT = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        self.CONNECTIONS_CHILD =  [0, 1, 2, 3, 0, 5, 6, 7, 0,  9, 10, 11,  0, 13, 14, 15,  0, 17, 18, 19]

        # Store angles to annotate
        # [landmark label, conn1, conn2]
        self.ANGLES_SHOW_FLAG = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
        self.ANGLES_SHOW_AT = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19, 5, 9, 13, 17]
        self.ANGLES_CONN1 = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19, 5, 9, 13, 17]
        self.ANGLES_CONN2 = [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, -1, -2, -3, -4]
        self.ANGLE_COUNT = len(self.ANGLES_SHOW_FLAG)

        # Coordinates, connections, and angels between connections
        self.landmarks = np.zeros((self.LANDMARK_COUNT, self.COORD_DIM))
        self.coord = np.zeros((self.LANDMARK_COUNT, self.COORD_DIM))
        self.conn = np.zeros((self.CONNECTION_COUNT, self.COORD_DIM))
        self.angle = np.zeros((self.ANGLE_COUNT))
        self.normal = np.zeros((self.NORMAL_COUNT, self.COORD_DIM))
        self.NORMAL_AT = [0, 5, 9, 13, 17]

        # Connections used to cross product with palm normal to calculate normal plane for MCP joints
        self.MCP_NORMAL_OPERAND_CONN = [ConnLabel.INDEX_FINGER_CB,
                                        ConnLabel.MIDDLE_FINGER_CB,
                                        ConnLabel.RING_FINGER_CB,
                                        ConnLabel.PINKY_FINGER_CB]

        # Store image
        self.image = np.zeros((480, 480, 3), np.uint8)

    def _calc_coordinates(self, results):
        for idx, landmark in enumerate(results.multi_hand_landmarks[0].landmark):
            self.coord[idx] = [landmark.x, landmark.y, landmark.z]
        return self.coord

    def _calc_connections(self, results):
        coords = self._calc_coordinates(results)
        normal = self.normal
        conn = self.conn
        for idx, (a, b) in enumerate(zip(self.CONNECTIONS_PARENT, self.CONNECTIONS_CHILD)):
            conn[idx] = coords[a] - coords[b]

        # Calculate palm normal
        normal[NormalLabel.PALM_NORMAL] = np.cross(
            conn[ConnLabel.PINKY_FINGER_CB], conn[ConnLabel.INDEX_FINGER_CB])

        for idx, idx_conn in enumerate(self.MCP_NORMAL_OPERAND_CONN):
            # Palm normal is in 0, so rest starts at 1
            normal[idx + 1] = np.cross(normal[NormalLabel.PALM_NORMAL], conn[idx_conn])
        print(normal)
        return conn

    def _angle_between(self, conn1, conn2):
        unit_conn1 = conn1 / np.linalg.norm(conn1)
        unit_conn2 = conn2 / np.linalg.norm(conn2)
        dot_product = np.dot(unit_conn1, unit_conn2)

        rad_angle = np.arccos(dot_product)
        deg_angle = rad_angle * 180 / np.pi

        return deg_angle

    def _calc_angles(self):
        for idx, (a, b) in enumerate(zip(self.ANGLES_CONN1, self.ANGLES_CONN2)):
            conn1 = self.normal[abs(a)] if (a < 0) else self.conn[a]
            conn2 = self.normal[abs(b)] if (b < 0) else self.conn[b]
            self.angle[idx] = self._angle_between(conn1, conn2)
        return self.angle

    #NEED TO FIX
    def _label_angles(self):
        # Maximum angle
        MAX_ANGLE = 180

        # Text params
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.7
        text_color = (0, 0, 0)
        text_thickness = 1

        # Rect params
        image_width, image_height = self.image.shape[:2]
        rect_color = (255, 255, 255)
        rect_border_color = (0, 0, 0)

        # Labelling
        for flag, loc_idx, angle in zip(self.ANGLES_SHOW_FLAG, self.ANGLES_SHOW_AT, self.angle):
            # Check if angle show flag set to 1 (True)
            if flag == 0:
                continue

            angle = min(MAX_ANGLE, angle)
            angle_text = str(math.floor(angle))
            (w, h), _ = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_DUPLEX, font_scale, text_thickness)

            loc = self.coord[loc_idx]
            x = math.floor(loc[0] * image_height)
            y = math.floor(loc[1] * image_width)

            image = cv2.rectangle(self.image, (x, y - h), (x + w, y), rect_color, -1)
            image = cv2.rectangle(self.image, (x, y - h), (x + w, y), rect_border_color, 1)
            image = cv2.putText(self.image, angle_text, (x, y), font, font_scale, text_color, text_thickness)

        return self.image

    def draw_angles(self, image, results):
        self.image = image

        self._calc_connections(results)
        self._calc_angles()
        self._label_angles()

        return image

    def get_coords(self):
        return self.coord
