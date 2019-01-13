import os
import numpy as np

import tensorflow as tf
USE_ALTERNATIVE = False
try:
    from tensorflow.data import Dataset
except ImportError:
    tf.logging.warning('Using alternative settings due to old TF version')
    Dataset = tf.data.Dataset
    USE_ALTERNATIVE = True


HEIGHT = WIDTH = 32
CHANNELS = 3

NOISE_DIMS = 64

def input_fn(params):
    """Read CIFAR input data from a TFRecord dataset.

    Function taken from tensorflow/tpu cifar_keras repo"""
    batch_size = params['batch_size']
    data_dir = params['data_dir']
    noise_dim = params['noise_dim']
    def parser(serialized_example):
        """Parses a single tf.Example into image and label tensors."""
        features = tf.parse_single_example(
            serialized_example,
            features={
                "image": tf.FixedLenFeature([], tf.string),
                "label": tf.FixedLenFeature([], tf.int64),
            })
        image = tf.decode_raw(features["image"], tf.uint8)
        image.set_shape([CHANNELS * HEIGHT * WIDTH])
        # Reshape from [depth * height * width] to [depth, height, width].
        image = tf.cast(
                tf.transpose(tf.reshape(image, [CHANNELS, HEIGHT, WIDTH]), [1, 2, 0]),
                tf.float32) * (2. / 255) - 1

        label = tf.cast(features['label'], tf.int32)

        random_noise = tf.random_normal([noise_dim])
        features = {
            'real_images': image,
            'random_noise': random_noise}

        return features, label

    # TODO we should use an eval dataset for EVAL  # pylint: disable=fixme
    image_files = [os.path.join(data_dir, 'train.tfrecords')]
    tf.logging.info(image_files)
    dataset = tf.data.TFRecordDataset([image_files])
    dataset = dataset.map(parser, num_parallel_calls=batch_size)
    dataset = dataset.prefetch(4 * batch_size).cache().repeat()
    if USE_ALTERNATIVE:
        dataset = dataset.apply(tf.contrib.data.batch_and_drop_remainder(batch_size))
        tf.logging.warning('Old version: Used tf.contrib.data.batch_and_drop_remainder instead of regular batch')
    else:
        dataset = dataset.batch(batch_size, drop_remainder=True)
    # Not sure why we use one_shot and not initializable_iterator
    features, labels = dataset.make_one_shot_iterator().get_next()

    return features, labels

# TODO Taken from cq500, not tested!
def noise_input_fn(params):
    """Input function for generating samples for PREDICT mode.

    Generates a single Tensor of fixed random noise. Use tf.data.Dataset to
    signal to the estimator when to terminate the generator returned by
    predict().

    Args:
        params: param `dict` passed by TPUEstimator.

    Returns:
        1-element `dict` containing the randomly generated noise.
    """
    batch_size = params['batch_size']
    noise_dim = params['noise_dim']
    # Use constant seed to obtain same noise
    np.random.seed(0)
    noise_dataset = tf.data.Dataset.from_tensors(
        {'random_noise': tf.constant(
            np.random.randn(batch_size, noise_dim), dtype=tf.float32)
        })
    noise = noise_dataset.make_one_shot_iterator().get_next()
    tf.logging.debug('Noise input %s', noise)
    return noise_dataset


def generate_input_fn(mode='TRAIN'):
    """Creates input_fn depending on whether the code is training or not."""
    mode = mode.upper()
    if mode == 'TRAIN' or mode == 'EVAL':
        return input_fn
    elif mode == 'PREDICT' or mode == 'NOISE':
        return noise_input_fn
    else:
        raise ValueError('Incorrect mode provided')