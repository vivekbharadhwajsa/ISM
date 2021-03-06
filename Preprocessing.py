import pandas as pd
import cv2
import os
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib import colors
from matplotlib.colors import hsv_to_rgb

class preprocessing:

    def __init__(self):
        self.path = Path("C:/Users/Vicky/Desktop")
        self.csv_path = os.path.join(self.path, "TUHH\ISM\Files")
        self.csv_name = "groundtruth_train"
        self.image_path = os.path.join(self.csv_path, "ISIC_2019_Training_Input")
        self.listdir = os.listdir(self.image_path)
        self.images = []
        for file in self.listdir:
            if file != 'ATTRIBUTION.txt':
                self.images.append(file)
        # self.img = cv2.resize(cv2.imread(os.path.join(self.image_path, self.images[50])), dsize=(700,700))
        self.img = cv2.resize(cv2.imread(os.path.join(self.image_path, 'ISIC_0000999_downsampled.jpg')), dsize=(700,700))

    def read_csvs(self):
        self.train_csv = pd.read_csv(self.csv_name)
        self.test_csv = pd.read_csv(os.path.join(self.csv_path, "groundtruth_val"))

    def convert_togray(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return gray

    def median_filter(self, image):
        median = cv2.medianBlur(image, 5)
        return median

    def apply_discmasking(self, image):
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        r, g, b = cv2.split(img)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)
        light_orange = (1, 100, 170)
        dark_orange = (18, 255, 255)
        light_blue = (50, 50, 75)
        dark_blue = (150, 250, 250)
        m = img.shape[0]
        n = img.shape[1]
        template = np.ones((m, n))
        template = template.astype(int)

        a = r.flatten()
        counts = np.bincount(a)
        r_max = np.argmax(counts)

        a = g.flatten()
        counts = np.bincount(a)
        g_max = np.argmax(counts)

        a = b.flatten()
        counts = np.bincount(a)
        b_max = np.argmax(counts)

        rn = template * r_max
        gn = template * g_max
        bn = template * b_max
        skin = np.dstack([rn, gn, bn])
        mask = cv2.inRange(hsv, light_orange, dark_orange)
        mask1 = cv2.inRange(hsv, light_blue, dark_blue)
        masker = cv2.bitwise_not(mask)
        m1 = cv2.bitwise_not(mask1)

        # replace the sticker with black
        imnew = cv2.bitwise_and(img, img, mask=masker)
        imnew = cv2.bitwise_and(imnew, imnew, mask=m1)
        skinPatch = cv2.bitwise_and(skin, skin, mask=mask)
        skinPatch1 = cv2.bitwise_and(skin, skin, mask=mask1)
        rst = cv2.add(imnew, skinPatch, dtype=cv2.CV_8UC1)
        rst = cv2.add(rst, skinPatch1, dtype=cv2.CV_8UC1)
        rst = rst.astype(np.uint8)

        return rst

    def apply_dullrazor(self, image):
        grayScale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        kernel = cv2.getStructuringElement(1, (17, 17))
        blackhat = cv2.morphologyEx(grayScale, cv2.MORPH_BLACKHAT, kernel)

        ret, thresh2 = cv2.threshold(blackhat, 10, 255, cv2.THRESH_BINARY)
        thresh3 = cv2.adaptiveThreshold(blackhat, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11,
                                        2)  # Adaptive gaussian
        thresh4 = cv2.adaptiveThreshold(blackhat, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11,
                                        2)  # Adaptive gaussian

        # inpaint the original image depending on the mask
        dst = cv2.inpaint(image, thresh2, 10, cv2.INPAINT_TELEA)

        return dst

    def apply_kmeans(self, image):

        Z = image.reshape((-1, 3))
        Z = np.float32(Z)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = 15
        ret, label, center = cv2.kmeans(Z, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        center = np.uint8(center)
        res = center[label.flatten()]
        kmeans_img = res.reshape((image.shape))
        # cv2.imshow("Kmeans img", kmeans_img)
        # cv2.waitKey(0)
        return kmeans_img

    def apply_AHE(self, image):
        clahe = cv2.createCLAHE(clipLimit=3., tileGridSize=(8,8))

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # cv2.imshow("HSV", hsv)
        # cv2.waitKey(0)

        h, s, v = cv2.split(hsv)

        h1 = clahe.apply(h)
        s1 = clahe.apply(s)
        v1 = clahe.apply(v)

        lab = cv2.merge((h1, s1, v1))
        # cv2.imshow("Lab", lab)
        # cv2.waitKey(0)
        
        enhanced_img = cv2.cvtColor(lab, cv2.COLOR_Lab2BGR)
        # cv2.imshow("Enhanced", enhanced_img)
        # cv2.waitKey(0)
        
        return hsv, lab, enhanced_img

    def grabcut_mask(self, image, enhancedimg):
        hsv_img = cv2.cvtColor(enhancedimg, cv2.COLOR_BGR2HSV)

        lower_green = np.array([50,100,100])
        higher_green = np.array([100,255,255])
        mask = cv2.inRange(hsv_img, lower_green, higher_green)
        # cv2.imshow("Mask", mask)
        # cv2.waitKey(0)

        ret, inv_mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY_INV)
        # cv2.imshow("Inv Mask", inv_mask)
        # cv2.waitKey(0)

        res = cv2.bitwise_and(image, image, mask=mask)
        # cv2.imshow("Res", res)
        # cv2.waitKey(0)

        new_mask = np.zeros(image.shape[:2], np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)

        if (np.sum(inv_mask[:]) < 80039400):
            newmask = inv_mask
            new_mask[newmask == 0] = 0
            new_mask[newmask == 255] = 1
            dim = cv2.grabCut(image, new_mask, None, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)
            mask2 = np.where((new_mask == 2) | (new_mask == 0), 0, 1).astype('uint8')
            GrabCut_img = image * mask2[:, :, np.newaxis]
            cv2.imshow("Grab img", GrabCut_img)
            cv2.waitKey(0)
        else:
            s = (int(image.shape[0] / 10), int(image.shape[1] / 10))
            rect = (s[0], s[1], int(image.shape[0] - (3 / 10) * s[0]), image.shape[1] - s[1])
            cv2.grabCut(enhancedimg, new_mask, rect, bgdModel, fgdModel, 10, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            GrabCut_img = image * mask2[:, :, np.newaxis]
            cv2.imshow("Grab img", GrabCut_img)
            cv2.waitKey(0)

            plt.imshow(GrabCut_img)
            plt.colorbar()
            plt.show()

        imgmask = cv2.medianBlur(GrabCut_img, 5)
        ret, Segmented_mask = cv2.threshold(imgmask, 0, 255, cv2.THRESH_BINARY)
        cv2.imshow("Seg Image", Segmented_mask)
        cv2.waitKey(0)

        if (np.sum(inv_mask[:]) < 80039400):
            newmask = inv_mask
            new_mask[newmask == 0] = 0
            new_mask[newmask == 255] = 1
            dim = cv2.grabCut(image, new_mask, None, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)
            mask2 = np.where((new_mask == 2) | (new_mask == 0), 0, 1).astype('uint8')
            GrabCut_img2 = image * mask2[:, :, np.newaxis]
            cv2.imshow("Grab img", GrabCut_img)
            cv2.waitKey(0)
        else:
            s = (int(image.shape[0] / 10), int(image.shape[1] / 10))
            rect = (s[0], s[1], int(image.shape[0] - (3 / 10) * s[0]), image.shape[1] - s[1])
            cv2.grabCut(enhancedimg, new_mask, rect, bgdModel, fgdModel, 10, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            GrabCut_img2 = image * mask2[:, :, np.newaxis]
            cv2.imshow("Grab img", GrabCut_img)
            cv2.waitKey(0)

        imgmask2 = cv2.medianBlur(GrabCut_img2, 5)
        ret, Segmented_mask2 = cv2.threshold(imgmask2, 0, 255, cv2.THRESH_BINARY)
        plt.imshow(GrabCut_img2)
        plt.colorbar()
        plt.show()

        return GrabCut_img2
    
if __name__ == '__main__':
    pre = preprocessing()
    image = pre.img
    # cv2.imshow("img", image)
    # cv2.waitKey(0)
    premask = pre.apply_discmasking(image)
    # cv2.imshow("Premask", premask)
    # cv2.waitKey(0)
    dst = pre.apply_dullrazor(premask)
    # cv2.imshow("Dull Razor", dst)
    # cv2.waitKey(0)
    med = pre.median_filter(dst)
    # cv2.imshow("median", med)
    # cv2.waitKey(0)
    km = pre.apply_kmeans(med)
    hsv, lab, enh = pre.apply_AHE(km)
    grab_img = pre.grabcut_mask(image ,enh)

    together =cv2.hconcat([image, grab_img])
    cv2.imshow("Final", together)
    cv2.waitKey(0)