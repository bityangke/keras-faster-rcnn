# -*- coding: utf-8 -*-
"""
Created on 2018/12/16 上午9:30

@author: mick.yi

训练frcnn

"""

import random
import numpy as np
from faster_rcnn.config import current_config as config
from faster_rcnn.preprocess.pascal_voc import get_voc_data
from faster_rcnn.utils.image import load_image_gt
from faster_rcnn.utils.np_utils import pad_to_fixed_size
from faster_rcnn.layers import models
from faster_rcnn.layers.models import compile
from keras.callbacks import TensorBoard, ReduceLROnPlateau, ModelCheckpoint


def generator(all_image_info, batch_size):
    image_length = len(all_image_info)
    id_list = range(image_length)
    while True:
        ids = random.sample(id_list, batch_size)
        batch_image = []
        batch_image_meta = []
        batch_class_ids = []
        batch_bbox = []

        for id in ids:
            image, image_meta, class_ids, bbox = load_image_gt(
                config, all_image_info[id], id)
            batch_image.append(image)
            batch_image_meta.append(image_meta)
            # gt个数固定
            batch_class_ids.append(pad_to_fixed_size(np.expand_dims(class_ids, axis=1), 50))
            batch_bbox.append(pad_to_fixed_size(bbox, 50))
        # print("np.asarray(batch_image).shape:{}".format(np.asarray(batch_image).shape))
        yield [np.asarray(batch_image),
               np.asarray(batch_image_meta),
               np.asarray(batch_class_ids),
               np.asarray(batch_bbox)], None


def get_call_back():
    """
    定义call back
    :return:
    """
    checkpoint = ModelCheckpoint(filepath='/tmp/frcnn-rpn.{epoch:03d}.h5',
                                 monitor='acc',
                                 verbose=1,
                                 save_best_only=False)

    # 验证误差没有提升
    lr_reducer = ReduceLROnPlateau(monitor='loss',
                                   factor=np.sqrt(0.1),
                                   cooldown=1,
                                   patience=1,
                                   min_lr=0)
    log = TensorBoard(log_dir='log')
    return [checkpoint, lr_reducer]


if __name__ == '__main__':
    from tensorflow.python import debug as tf_debug
    import keras.backend as K

    # sess = K.get_session()
    # sess = tf_debug.LocalCLIDebugWrapperSession(sess)
    # sess.add_tensor_filter("has_inf_or_nan", tf_debug.has_inf_or_nan)
    #
    # K.set_session(sess)

    # voc_path = '/Users/yizuotian/dataset/VOCdevkit/'
    # voc_path = 'd:\work\图像识别\VOCtrainval_06-Nov-2007\VOCdevkit'
    # voc_path = '/opt/dataset/VOCdevkit'
    all_img_info, classes_count, class_mapping = get_voc_data(config.voc_path)
    print("all_img_info:{}".format(len(all_img_info)))
    # m = rpn_net((config.IMAGE_MAX_DIM, config.IMAGE_MAX_DIM, 3), 50, config.IMAGES_PER_GPU)
    m = models.frcnn((config.IMAGE_MAX_DIM, config.IMAGE_MAX_DIM, 3), config.BATCH_SIZE, config.NUM_CLASSES,
                     50, config.IMAGE_MAX_DIM, config.TRAIN_ROIS_PER_IMAGE, config.ROI_POSITIVE_RATIO)
    m.load_weights(config.pretrained_weights, by_name=True)
    # m.load_weights('resnet50_weights_tf_dim_ordering_tf_kernels_notop.h5', by_name=True)
    compile(m, config, 1e-4, 0.9)
    m.summary()

    m.fit_generator(generator(all_img_info, config.IMAGES_PER_GPU),
                    epochs=10,
                    steps_per_epoch=len(all_img_info) // config.IMAGES_PER_GPU,
                    verbose=1,
                    callbacks=get_call_back())
