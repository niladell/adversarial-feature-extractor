"""Prototype run file

Example run command:
python src/run_tpu.py --model_dir=gs://[BUCKET_NAME]/cifar10/outputs --data_dir=gs://[BUCKET_NAME]/cifar10/data  --tpu=[TPU_NAME]
"""

import sys
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(filename)s: '
                            '%(levelname)s: '
                            '%(funcName)s(): '
                            '%(lineno)d:\t'
                            '%(message)s')
from absl import flags
import tensorflow as tf
# TODO ¿move all to normal logging module?
# tf.logging.set_verbosity(tf.logging.INFO)

FLAGS = flags.FLAGS


# Cloud TPU Cluster Resolvers
flags.DEFINE_boolean('use_tpu', True, 'Use TPU for training')
flags.DEFINE_string(
    'tpu', default='node-1',
    help='The Cloud TPU to use for training. This should be either the name '
    'used when creating the Cloud TPU, or a grpc://ip.address.of.tpu:8470 url.')
flags.DEFINE_string(
    'gcp_project', default=None,
    help='Project name for the Cloud TPU-enabled project. If not specified, we '
    'will attempt to automatically detect the GCE project from metadata.')
flags.DEFINE_string(
    'tpu_zone', default='us-central1-f',
    help='GCE zone where the Cloud TPU is located in. If not specified, we '
    'will attempt to automatically detect the GCE project from metadata.')
flags.DEFINE_integer('num_shards', None, 'Number of TPU chips')

# Model specific paramenters
flags.DEFINE_string('model_dir', '', 'Output model directory')
flags.DEFINE_string('data_dir', '', 'Dataset directory')
flags.DEFINE_string('dataset', 'CIFAR10', 'Which dataset to use')
flags.DEFINE_integer('noise_dim', 64,
                     'Number of dimensions for the noise vector')
flags.DEFINE_integer('batch_size', 1024,
                     'Batch size for both generator and discriminator')
flags.DEFINE_integer('train_steps', 50000, 'Number of training steps')
flags.DEFINE_integer('train_steps_per_eval', 5000,
                     'Steps per eval and image generation')
flags.DEFINE_integer('num_eval_images', 1024,
                     'Number of images on the evaluation')
flags.DEFINE_integer('num_viz_images', 100,
                     'Number of images generated on each PREDICT')
flags.DEFINE_integer('iterations_per_loop', 200,
                     'Steps per interior TPU loop. Should be less than'
                     ' --train_steps_per_eval')
flags.DEFINE_float('learning_rate', 0.0002, 'LR for both D and G')
flags.DEFINE_boolean('eval_loss', True,
                     'Evaluate discriminator and generator loss during eval')


if __name__ == "__main__":
    FLAGS(sys.argv)

    from model import Model
    if FLAGS.dataset == 'CIFAR10':
        from datamanager.CIFAR_input_functions import generate_input_fn
    elif FLAGS.dataset == 'celebA':
        from datamanager.celebA_input_functions import generate_input_fn

    model = Model(model_dir=FLAGS.model_dir, data_dir=FLAGS.data_dir, dataset=FLAGS.dataset,
                # Model parameters
                learning_rate=FLAGS.learning_rate, batch_size=FLAGS.batch_size, noise_dim=FLAGS.noise_dim,
                # Training and prediction settings
                iterations_per_loop=FLAGS.iterations_per_loop, num_viz_images=FLAGS.num_viz_images,
                # Evaluation settings
                eval_loss=FLAGS.eval_loss, train_steps_per_eval=FLAGS.train_steps_per_eval,
                num_eval_images=FLAGS.num_eval_images,
                # TPU settings
                use_tpu=FLAGS.use_tpu, tpu=FLAGS.tpu, tpu_zone=FLAGS.tpu_zone,
                gcp_project=FLAGS.gcp_project, num_shards=FLAGS.num_shards)

    model.save_samples_from_data(generate_input_fn)
    model.build_model()
    model.train(FLAGS.train_steps, generate_input_fn)
    tf.logging.info('Finished!')
