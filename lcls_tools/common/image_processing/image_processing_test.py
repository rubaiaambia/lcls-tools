import sys
import unittest
import numpy as np
import image_processing as ip
from mat_image import MatImage

FILE = './test_image_electron.mat'
CAMERA = 'CAMR:LGUN:210'

class ImageProcessingTest(unittest.TestCase):
    
    def setUp(self):
        """Use test image"""
        self.MI = MatImage()
        self.MI.load_mat_image(FILE)

    def test_fliplr(self):
        """Test that fliplr does the right thing"""
        col_init = self.MI.image[:, 0]
        col_final = ip.fliplr(self.MI.image)[:, -1]
        self.assertEqual(np.array_equal(col_init, col_final), True)

    def test_flipud(self):
        """Test that flipud does the right thing"""
        row_init = self.MI.image[0]
        row_final = ip.flipud(self.MI.image)[-1]
        self.assertEqual(np.array_equal(row_init, row_final), True)

    def test_center_of_mass(self):
        """Test that we get correct x and y centroids"""
        (x1, y1) = ip.center_of_mass(self.MI.image)
        self.assertEqual((int(x1), int(y1)), (502, 722))
        (x2, y2) = ip.center_of_mass(self.MI.image, sigma=2)
        self.assertEqual((int(x2), int(y2)), (502, 724))

    def test_average_image(self):
        """Test that we can average a number of images"""
        images = []
        while len(images) < 10:
            images.append(self.MI.image)
        ave_image = ip.average_image(images)
        self.assertEqual(np.array_equal(ave_image, self.MI.image), True)

    def test_shape_image(self):
        """Test that we can reshape our ndarray"""
        print(self.MI.image)
        self.assertEqual(self.MI.image.shape, (1040, 1392))
        image = ip.shape_image(self.MI.image, 1040, 1392)
        self.assertEqual(image.shape, (1392, 1040))

    def test_x_projection(self):
        """Test we get expected value for x projection"""
        x_proj = ip.x_projection(self.MI.image)
        self.assertEqual(x_proj.sum(), 121978875)
        self.assertEqual(int(x_proj.mean()), 87628)
        self.assertEqual(int(x_proj.std()), 31132)

    def test_y_projection(self):
        """Test that we get expected value for y projection"""
        y_proj = ip.y_projection(self.MI.image)
        self.assertEqual(y_proj.sum(), 22103515)
        self.assertEqual(int(y_proj.mean()), 21253)
        self.assertEqual(int(y_proj.std()), 34331)

    def test_gauss_func(self):
        """Test we get correct value for a gaussian evaluation"""
        ans = ip.gauss_func(1.0, 2.0, 3.0, 4.0)
        self.assertEqual(round(ans, 2), 1.76)

    def test_gauss_fit(self):
        """Test that we get the correct gaussian fit parameters"""
        x_proj = ip.x_projection(self.MI.image)
        y_proj = ip.y_projection(self.MI.image)
        _, a_x, x0_x, sigma_x = ip.gauss_fit(x_proj)
        _, a_y, y0_y, sigma_y = ip.gauss_fit(y_proj)
        self.assertEqual(int(a_x), 152483)
        self.assertEqual(int(x0_x), 722)
        self.assertEqual(int(sigma_x), 25)
        self.assertEqual(int(a_y), 187259)
        self.assertEqual(int(y0_y), 500)
        self.assertEqual(int(sigma_y), 20)

if __name__ == '__main__':
    unittest.main()
        
