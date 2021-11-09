import random
import math
import os
import shutil
import numpy
import cv2

SOURCE_DATASET = 'nilfdb'
CONTRAST_BOUNDS = (0.8, 1.3)
BRIGHTNESS_BOUNDS = (-20, 20)
BLUR_BOUNDS = (-1.3, 1.1)
COLOR_BOUNDS = (-15, 15)
PADDING_VALUE = 0
NOISE_VARIANCE = 1.0
TRANSLATION_BOUNDS = ((-30, 30), (-10, 10))
ROTATION_BOUNDS = (-20, 20)
SCALE_BOUNDS = (0.9, 1.1)
SHEAR_BOUNDS = (-0.1, 0.1)

def pad_scale(image, target_size, gray_value):
    height = image.shape[0]
    width = image.shape[1]
    if height >= width:
        target_height = target_size
        target_width = round(width / height * target_height)
        raw_padding = (target_height - target_width) / 2
        padding = (0,0,math.ceil(raw_padding),math.floor(raw_padding))
    else:
        target_width = target_size
        target_height = round(height / width * target_width)
        raw_padding = (target_width - target_height) / 2
        padding = (math.ceil(raw_padding),math.floor(raw_padding),0,0)
    resized_image = cv2.resize(image, (target_width, target_height))
    padded_image = cv2.copyMakeBorder(resized_image, padding[0], padding[1], padding[2], padding[3], cv2.BORDER_CONSTANT, value=(gray_value,gray_value,gray_value))
    return padded_image

def naive_correction(image, contrast, brightness):
    corrected_image = image.astype(numpy.int32) * contrast + brightness
    clipped_image = numpy.clip(corrected_image, 0, 255).astype(numpy.uint8)
    return clipped_image

def blur_sharpen(image, amount):
    if amount >= 0:
        sigma = amount
        size = int(2 * math.ceil(3 * sigma) + 1)
        enhanced_image = cv2.GaussianBlur(image, (size,size), sigma)
    else:
        kernel = numpy.array([[0,0,0],[0,1,0],[0,0,0]]) + numpy.array([[0,-1,0],[-1,4,-1],[0,-1,0]]) * -amount
        sharpened_image = cv2.filter2D(image.astype(float), -1, kernel, (-1,-1))
        enhanced_image = numpy.clip(sharpened_image, 0, 255).astype(numpy.uint8)
    return enhanced_image

def add_gaussian_noise(image, variance):
    mean = 0.0
    noise = numpy.random.normal(mean, variance, image.shape)
    noisy_image = image.astype(numpy.int32) + noise
    clipped_image = numpy.clip(noisy_image, 0, 255).astype(numpy.uint8)
    return clipped_image

def affine_transform(image, translation, rotation, scale, gray_value, shear=0):
    center = (round(image.shape[1]/2), round(image.shape[0]/2))
    size = (image.shape[1],image.shape[0])
    rotation_matrix = cv2.getRotationMatrix2D(center, rotation, scale)
    rotated_image = cv2.warpAffine(image, rotation_matrix, size, cv2.BORDER_CONSTANT, borderValue=(gray_value,gray_value,gray_value))
    translation_matrix = numpy.float32([[1,shear,translation[0]],[0,1,translation[1]]])
    translated_image = cv2.warpAffine(rotated_image, translation_matrix, size, cv2.BORDER_CONSTANT, borderValue=(gray_value,gray_value,gray_value))
    return translated_image

def recolor(image, red, green, blue):
    recolored_image = image[:,:] + (red,green,blue)
    clipped_image = numpy.clip(recolored_image, 0, 255).astype(numpy.uint8)
    return clipped_image

def generate_augmentation(image, verbose=False):
    result_image = image.copy()
    contrast = random.randint(round(CONTRAST_BOUNDS[0]*1000), round(CONTRAST_BOUNDS[1]*1000)) * 0.001
    brightness = random.randint(*BRIGHTNESS_BOUNDS)
    blur = random.randint(round(BLUR_BOUNDS[0]*1000), round(BLUR_BOUNDS[1]*1000)) * 0.001
    noise = NOISE_VARIANCE
    translation = (random.randint(*TRANSLATION_BOUNDS[0]),random.randint(*TRANSLATION_BOUNDS[1]))
    rotation = random.randint(*ROTATION_BOUNDS)
    scale = random.randint(round(SCALE_BOUNDS[0]*1000), round(SCALE_BOUNDS[1]*1000)) * 0.001
    shear = random.randint(round(SHEAR_BOUNDS[0]*1000), round(SHEAR_BOUNDS[1]*1000)) * 0.001
    color = (random.randint(*COLOR_BOUNDS), random.randint(*COLOR_BOUNDS), random.randint(*COLOR_BOUNDS))
    background = PADDING_VALUE
    result_image = affine_transform(result_image, translation, rotation, scale, background, shear=shear)
    result_image = recolor(result_image,*color)
    result_image = add_gaussian_noise(result_image, noise)
    result_image = naive_correction(result_image, contrast, brightness)
    result_image = blur_sharpen(result_image, blur)
    if verbose:
        print('CONT:', contrast, 'BRIG:', brightness, 'BLUR:', blur, 'NOIS:', noise, 'TRAN', translation, 'ROTA', rotation, 'SCAL', scale, 'COLO', color, 'BACK', background)
    return result_image

def determine_split(samples_count, train_split, validation_split, test_split):
    train_size = round(samples_count * train_split / 100)
    validation_size = round(samples_count * validation_split / 100)
    test_size = round(samples_count * test_split / 100)
    train_size = train_size if train_size > 0 else 1
    validation_size = validation_size if validation_size > 0 else 1
    test_size = test_size if test_size > 0 else 1
    train_size += samples_count - train_size - validation_size - test_size
    return train_size, validation_size, test_size

def save_class_tf(label, samples, destination_directory, target_size, augmentation=0):
    destination_book_path = '{}/images'.format(destination_directory)
    if not os.path.exists(destination_book_path):
        os.makedirs(destination_book_path)
    augmented_samples = samples * math.ceil(augmentation / len(samples)) if augmentation > len(samples) else samples
    base_number = len(os.listdir(destination_book_path))
    with open('{}/labels.txt'.format(destination_directory), 'a') as labels_file:
        for i in range(0, max(augmentation, len(samples))):
            picture_in = cv2.cvtColor(cv2.imread(augmented_samples[i]), cv2.COLOR_BGR2RGB)
            reshaped_picture = pad_scale(picture_in, target_size, PADDING_VALUE)
            if i < len(samples):
                picture_out = reshaped_picture
            else:
                picture_out = generate_augmentation(reshaped_picture)
            cv2.imwrite('{}/{}.jpg'.format(destination_book_path, str(base_number + i)), cv2.cvtColor(picture_out, cv2.COLOR_RGB2BGR))
            labels_file.write('{}\n'.format(label))

def save_class_pt(label, samples, destination_directory, target_size, augmentation=0):
    destination_book_path = '{}/{}'.format(destination_directory, label)
    if not os.path.exists(destination_book_path):
        os.makedirs(destination_book_path)
    augmented_samples = samples * math.ceil(augmentation / len(samples)) if augmentation > len(samples) else samples
    for i in range(0, max(augmentation, len(samples))):
        picture_in = cv2.cvtColor(cv2.imread(augmented_samples[i]), cv2.COLOR_BGR2RGB)
        reshaped_picture = pad_scale(picture_in, target_size, PADDING_VALUE)
        if i < len(samples):
            picture_out = reshaped_picture
        else:
            picture_out = generate_augmentation(reshaped_picture)
        cv2.imwrite('{}/{}.jpg'.format(destination_book_path, str(i)), cv2.cvtColor(picture_out, cv2.COLOR_RGB2BGR))

def generate_dataset(source_directory, destination_directory, class_saver, target_size, train_split, validation_split, test_split, train_augmentation):
    train_directory = '{}/{}'.format(destination_directory, 'train')
    validation_directory = '{}/{}'.format(destination_directory, 'validation')
    test_directory = '{}/{}'.format(destination_directory, 'test')
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)
    with open('{}/classes.txt'.format(destination_directory), 'w') as classes_file:
        for i, book in enumerate(os.listdir(source_directory)):
            source_book_path = '{}/{}'.format(source_directory, book)
            samples = ['{}/{}'.format(source_book_path, x) for x in os.listdir(source_book_path) if x != 'card.txt']
            train_size, validation_size, test_size = determine_split(len(samples), train_split, validation_split, test_split)
            random.shuffle(samples)
            train_set = samples[0:train_size]
            validation_set = samples[train_size:train_size+validation_size]
            test_set = samples[train_size+validation_size:train_size+validation_size+test_size]
            label = book[4:]
            class_saver(label, train_set, train_directory, target_size, train_augmentation)
            class_saver(label, validation_set, validation_directory, target_size, 0)
            class_saver(label, test_set, test_directory, target_size, 0)
            with open('{}/card.txt'.format(source_book_path), 'r') as card_file:
                data = card_file.read().splitlines()
            classes_file.write('{}\t{}\t{}\n'.format(data[2], data[0], data[1]))
            print('BOOK {}/{} lab={} tra={} val={} tes={}'.format(i+1, len(os.listdir(source_directory)), label, train_size, validation_size, test_size))

# generate_dataset(SOURCE_DATASET, 'cyberset_tf_128', save_class_tf, target_size=128, train_split=70, validation_split=20, test_split=10, train_augmentation=60)
# shutil.make_archive('cyberset_tf_128', 'zip', '.', 'cyberset_tf_128')
# generate_dataset(SOURCE_DATASET, 'cyberset_tf_56', save_class_tf, target_size=56, train_split=70, validation_split=20, test_split=10, train_augmentation=60)
# shutil.make_archive('cyberset_tf_56', 'zip', '.', 'cyberset_tf_56')
# generate_dataset(SOURCE_DATASET, 'cyberset_tf_96', save_class_tf, target_size=96, train_split=70, validation_split=20, test_split=10, train_augmentation=60)
# shutil.make_archive('cyberset_tf_96', 'zip', '.', 'cyberset_tf_96')

# generate_dataset(SOURCE_DATASET, 'fairset_good_227', save_class_pt, target_size=227, train_split=70, validation_split=20, test_split=10, train_augmentation=60)
# generate_dataset(SOURCE_DATASET, 'fairset_good_224', save_class_pt, target_size=224, train_split=70, validation_split=20, test_split=10, train_augmentation=60)
# generate_dataset(SOURCE_DATASET, 'fairset_good_299', save_class_pt, target_size=299, train_split=70, validation_split=20, test_split=10, train_augmentation=60)

print('DONE')
