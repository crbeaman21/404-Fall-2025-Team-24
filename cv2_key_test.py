# cv2_key_test.py
import cv2
import numpy as np

img = np.zeros((200, 200, 3), dtype=np.uint8)

while True:
    cv2.imshow("KeyTest", img)
    key = cv2.waitKey(30) & 0xFF
    if key != 255:
        print("Key code:", key, "char:", repr(chr(key)))
    if key == ord('q'):
        break

cv2.destroyAllWindows()
