from __future__ import division
import os
import time
from glob import glob
import tensorflow as tf
import numpy as np
from six.moves import xrange
import sys

from ops import *
from utils import *

import matplotlib.pyplot as plt

class pix2pix(object):
    def __init__(self, sess, image_size=256,
                 batch_size=2, sample_size=1, output_size=256,
                 gf_dim=64, df_dim=64, L1_lambda=100, latent_lambda=1, ssim_lambda=1,
                 input_c_dim=3, output_c_dim=3, dataset_name='facades',
                 checkpoint_dir=None, load_checkpoint=False, sample_dir=None,
                 n_z=256, test_name='baseline_test'):
        """

        Args:
            sess: TensorFlow session
            batch_size: The size of batch. Should be specified before training.
            output_size: (optional) The resolution in pixels of the images. [256]
            gf_dim: (optional) Dimension of gen filters in first conv layer. [64]
            df_dim: (optional) Dimension of discrim filters in first conv layer. [64]
            input_c_dim: (optional) Dimension of input image color. For grayscale input, set to 1. [3]
            output_c_dim: (optional) Dimension of output image color. For grayscale input, set to 1. [3]
        """
        self.sess = sess
        self.is_grayscale = (input_c_dim == 1)
        self.batch_size = batch_size
        self.image_size = image_size
        self.sample_size = sample_size
        self.output_size = output_size
        self.n_z = n_z

        self.gf_dim = gf_dim
        self.df_dim = df_dim

        self.input_c_dim = input_c_dim
        self.output_c_dim = output_c_dim

        self.L1_lambda = L1_lambda
        self.latent_lambda = latent_lambda
        self.ssim_lambda = ssim_lambda
        self.test_name = test_name

        # batch normalization : deals with poor initialization helps gradient flow
        self.d_bn1 = batch_norm(name='d_bn1')
        self.d_bn2 = batch_norm(name='d_bn2')
        self.d_bn3 = batch_norm(name='d_bn3')

        self.g_bn_e2 = batch_norm(name='g_bn_e2')
        self.g_bn_e3 = batch_norm(name='g_bn_e3')
        self.g_bn_e4 = batch_norm(name='g_bn_e4')
        self.g_bn_e5 = batch_norm(name='g_bn_e5')
        self.g_bn_e6 = batch_norm(name='g_bn_e6')
        self.g_bn_e7 = batch_norm(name='g_bn_e7')
        self.g_bn_e8 = batch_norm(name='g_bn_e8')

        self.g_bn_d1 = batch_norm(name='g_bn_d1')
        self.g_bn_d2 = batch_norm(name='g_bn_d2')
        self.g_bn_d3 = batch_norm(name='g_bn_d3')
        self.g_bn_d4 = batch_norm(name='g_bn_d4')
        self.g_bn_d5 = batch_norm(name='g_bn_d5')
        self.g_bn_d6 = batch_norm(name='g_bn_d6')
        self.g_bn_d7 = batch_norm(name='g_bn_d7')

        self.dataset_name = dataset_name
        self.checkpoint_dir = checkpoint_dir
        self.load_checkpoint = load_checkpoint
        self.build_model()

    def build_model(self):
        self.real_data = tf.placeholder(tf.float32,
                                        [self.batch_size, self.image_size, self.image_size,
                                         self.input_c_dim + self.output_c_dim],
                                        name='real_A_and_B_images')

        self.real_B = self.real_data[:, :, :, :self.input_c_dim]
        self.real_A = self.real_data[:, :, :, self.input_c_dim:self.input_c_dim + self.output_c_dim]
 
        rand1 = tf.random_uniform([1])
        rand2 = tf.random_uniform([1])
        # noise1 = tf.random_uniform(self.real_A.shape[:-1].as_list() + [1,])
        # noise2 = tf.random_uniform(self.real_A.shape[:-1].as_list() + [1,])
        noise1 = tf.fill(self.real_A.shape[:-1].as_list() + [1,], rand1[0])
        noise2 = tf.fill(self.real_A.shape[:-1].as_list() + [1,], rand2[0])
        self.real_A_noisy1 = tf.concat([self.real_A, noise1], 3)
        self.real_A_noisy2 = tf.concat([self.real_A, noise2], 3)

        self.real_A2 = tf.concat([self.real_A_noisy1, self.real_A_noisy2], 0)
        # self.real_A2 = tf.concat([self.real_A, self.real_A], 0)


        # Original shape: [1, 256, 256, 3]
        # New shape:      [1, 2, 256, 256, 3]

        self.fake_B = self.generator(self.real_A2)

        print 'real A', self.real_A.shape
        print 'real B', self.real_B.shape
        print 'fake B', self.fake_B.shape

        self.real_AB = tf.concat([self.real_A, self.real_B], 3)
        # make real_AB same shape
        # self.real_AB = tf.concat([self.real_AB, self.real_AB], 0)

        print self.real_AB.shape

        # Loop through extra output dimension, usually of size 2.
        fake_AB_pairs = []

        for index in range(self.fake_B.shape[0]):
            fake_AB_pairs.append(tf.concat([self.real_A[index%int(self.real_A.shape[0]): index%int(self.real_A.shape[0])+1, ...], self.fake_B[index: index+1, ...]], 3))

        # self.fake_AB will have batch size of fake_B.shape[1]*batch_size.
        self.fake_AB = tf.concat(fake_AB_pairs, 0)

        #self.fake_AB = tf.concat([self.real_A, self.fake_B], 3)


        self.D, self.D_logits = self.discriminator(self.real_AB, reuse=False)
        self.D_, self.D_logits_ = self.discriminator(self.fake_AB, reuse=True)


        self.fake_B_sample = self.sampler(self.real_A2)
 

        self.d_sum = tf.summary.histogram("d", self.D)
        self.d__sum = tf.summary.histogram("d_", self.D_[:1])
        self.fake_B_sum = tf.summary.image("fake_B", self.fake_B[:1])
  
        self.d_loss_real = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits, labels=tf.ones_like(self.D)))
        self.d_loss_fake = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_, labels=tf.zeros_like(self.D_)))
        
        # self.fake_B_norm_1 = self.fake_B[0] - tf.reduce_mean(self.fake_B[0])
        # self.fake_B_norm_2 = self.fake_B[1] - tf.reduce_mean(self.fake_B[1])

        self.fake_B_norm_1 = self.fake_B[0]
        self.fake_B_norm_2 = self.fake_B[1]

        # self.g_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_, labels=tf.ones_like(self.D_))) \
        #                 - 5*tf.reduce_mean(tf.abs(self.fake_B_norm_1 - self.fake_B_norm_2)) \
        #                 + self.L1_lambda * tf.reduce_mean(tf.abs(self.real_B - self.fake_B))

        self.fake_B_norm_1 = tf.expand_dims(self.fake_B_norm_1, 0)
        self.fake_B_norm_2 = tf.expand_dims(self.fake_B_norm_2, 0)

        # make real_B same shape
        self.real_B = tf.concat([self.real_B, self.real_B], 0)

        # self.avg_channel_diff = tf.nn.moments(tf.abs(self.fake_B_norm_1 - self.fake_B_norm_2), axes=[0,1,2])[0]
        self.avg_channel_diff0 = tf.reduce_mean(tf.abs(self.fake_B_norm_1[:,:,:,0] - self.fake_B_norm_2[:,:,:,0]))
        self.avg_channel_diff1 = tf.reduce_mean(tf.abs(self.fake_B_norm_1[:,:,:,1] - self.fake_B_norm_2[:,:,:,1]))
        self.avg_channel_diff2 = tf.reduce_mean(tf.abs(self.fake_B_norm_1[:,:,:,2] - self.fake_B_norm_2[:,:,:,2]))

        self.channel_std0 = tf.sqrt(tf.nn.moments(self.fake_B_norm_1, axes=[0,1,2])[1])
        self.channel_std1 = tf.sqrt(tf.nn.moments(self.fake_B_norm_2, axes=[0,1,2])[1])

        self.latent_loss = tf.reduce_mean(0.5 * tf.reduce_sum(tf.square(self.z_mu) + tf.square(self.z_sigma) - tf.log(tf.square(self.z_sigma)) -1, 1))
        self.ssim_loss = self.tf_ssim(self.fake_B_norm_1, self.fake_B_norm_2)
        self.L1_loss = tf.reduce_mean(tf.abs(self.real_B - self.fake_B))
        self.L2_loss = tf.sqrt(tf.reduce_sum(tf.square(self.real_B - self.fake_B))) / tf.cast(tf.size(self.real_B), tf.float32)
        self.base_g_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_, labels=tf.ones_like(self.D_))) \
                            + self.L1_lambda * self.L1_loss

        self.g_loss = self.base_g_loss \
                        + self.latent_lambda * self.latent_loss \
                        + self.ssim_lambda * self.ssim_loss \

        #self.g_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_, labels=tf.ones_like(self.D_))) \
        #                + self.L1_lambda * tf.reduce_mean(tf.abs(self.real_B - self.fake_B))

        self.d_loss_real_sum = tf.summary.scalar("d_loss_real", self.d_loss_real)
        self.d_loss_fake_sum = tf.summary.scalar("d_loss_fake", self.d_loss_fake)

        self.d_loss = self.d_loss_real + self.d_loss_fake

        self.g_loss_sum = tf.summary.scalar("g_loss", self.g_loss)
        self.d_loss_sum = tf.summary.scalar("d_loss", self.d_loss)

        t_vars = tf.trainable_variables()

        self.d_vars = [var for var in t_vars if 'd_' in var.name]
        self.g_vars = [var for var in t_vars if 'g_' in var.name]

        self.saver = tf.train.Saver()


    def load_random_samples(self):
        data = np.random.choice(glob('./datasets/{}/val/*.jpg'.format(self.dataset_name)), self.batch_size)
        sample = [load_data(sample_file) for sample_file in data]

        if (self.is_grayscale):
            sample_images = np.array(sample).astype(np.float32)[:, :, :, None]
        else:
            sample_images = np.array(sample).astype(np.float32)
        return sample_images

    def sample_model(self, sample_dir, epoch, idx):
        sample_images = self.load_random_samples()
        samples, d_loss, g_loss = self.sess.run(
            [self.fake_B_sample, self.d_loss, self.g_loss],
            feed_dict={self.real_data: sample_images}
        )

        save_images(samples, [self.batch_size*2, 1],
                    './{}/{}_{:02d}_{:04d}.png'.format(sample_dir, self.test_name, epoch, idx))
        print("[Sample] d_loss: {:.8f}, g_loss: {:.8f}".format(d_loss, g_loss))

    def train(self, args):
        """Train pix2pix"""
        d_optim = tf.train.AdamOptimizer(args.lr, beta1=args.beta1) \
                          .minimize(self.d_loss, var_list=self.d_vars)
        g_optim = tf.train.AdamOptimizer(args.lr, beta1=args.beta1) \
                          .minimize(self.g_loss, var_list=self.g_vars)

        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)

        self.g_sum = tf.summary.merge([self.d__sum,
            self.fake_B_sum, self.d_loss_fake_sum, self.g_loss_sum])
        self.d_sum = tf.summary.merge([self.d_sum, self.d_loss_real_sum, self.d_loss_sum])
        self.writer = tf.summary.FileWriter("./logs", self.sess.graph)

        counter = 1
        start_time = time.time()

        if self.load_checkpoint and self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")

        data = glob('./datasets/{}/train/*.jpg'.format(self.dataset_name))
        # if False:
        #     image_data = np.array([load_data(file) for file in data])
        #     print 'image data shape save', image_data.shape
        #     np.save('facades.npy', image_data)
        # else:
        #     image_data = np.load('facades.npy')
        #     print 'image data shape load', image_data.shape
        g_losses = []
        base_g_losses = []
        latent_losses = []
        ssim_losses = []
        L1_losses = []
        L2_losses = []

        avg_channel_diffs0 = []
        avg_channel_diffs1 = []
        avg_channel_diffs2 = []

        channel_stds00 = []
        channel_stds01 = []
        channel_stds02 = []
        channel_stds10 = []
        channel_stds11 = []
        channel_stds12 = []

        for epoch in xrange(args.epoch):
            # data = glob('./datasets/{}/train/*.jpg'.format(self.dataset_name))
            #np.random.shuffle(data)
            batch_idxs = min(len(data), args.train_size) // self.batch_size

            curr_g_loss = 0
            curr_base_g_loss = 0
            curr_latent_loss = 0
            curr_ssim_loss = 0
            curr_L1_loss = 0
            curr_L2_loss = 0

            curr_avg_channel_diff0 = 0
            curr_avg_channel_diff1 = 0
            curr_avg_channel_diff2 = 0

            curr_channel_std00 = 0
            curr_channel_std01 = 0
            curr_channel_std02 = 0
            curr_channel_std10 = 0
            curr_channel_std11 = 0
            curr_channel_std12 = 0

            for idx in xrange(0, batch_idxs):
                if True:
                    batch_files = data[idx*self.batch_size:(idx+1)*self.batch_size]
                    batch = [load_data(batch_file) for batch_file in batch_files]
                else:
                    batch = image_data[idx*self.batch_size:(idx+1)*self.batch_size]
                if (self.is_grayscale):
                    batch_images = np.array(batch).astype(np.float32)[:, :, :, None]
                else:
                    batch_images = np.array(batch).astype(np.float32)

                # Update D network
                _, summary_str = self.sess.run([d_optim, self.d_sum],
                                               feed_dict={ self.real_data: batch_images })
                self.writer.add_summary(summary_str, counter)

                # Update G network
                _, summary_str = self.sess.run([g_optim, self.g_sum],
                                               feed_dict={ self.real_data: batch_images })
                self.writer.add_summary(summary_str, counter)

                # Run g_optim twice to make sure that d_loss does not go to zero (different from paper)
                _, summary_str = self.sess.run([g_optim, self.g_sum],
                                               feed_dict={ self.real_data: batch_images })
                self.writer.add_summary(summary_str, counter)

                _, summary_str = self.sess.run([g_optim, self.g_sum],
                                               feed_dict={ self.real_data: batch_images })
                self.writer.add_summary(summary_str, counter)

                _, summary_str = self.sess.run([g_optim, self.g_sum],
                                               feed_dict={ self.real_data: batch_images })
                self.writer.add_summary(summary_str, counter)

                errD_fake = self.d_loss_fake.eval({self.real_data: batch_images})
                errD_real = self.d_loss_real.eval({self.real_data: batch_images})
                errG = self.g_loss.eval({self.real_data: batch_images})
                
                counter += 1
                print("Epoch: [%2d] [%4d/%4d] time: %4.4f, d_loss: %.8f, g_loss: %.8f" \
                    % (epoch, idx, batch_idxs,
                        time.time() - start_time, errD_fake+errD_real, errG))

                # if np.mod(counter, 100) == 1:
                if np.mod(counter, 50) == 1:
                    self.sample_model(args.sample_dir, epoch, idx)

                if np.mod(counter, 500) == 2:
                    self.save(args.checkpoint_dir, counter)

                curr_g_loss += errG / batch_idxs
                curr_base_g_loss += self.base_g_loss.eval({self.real_data: batch_images}) / batch_idxs
                curr_latent_loss += self.latent_loss.eval({self.real_data: batch_images}) / batch_idxs
                curr_ssim_loss += self.ssim_loss.eval({self.real_data: batch_images}) / batch_idxs
                curr_L1_loss += self.L1_loss.eval({self.real_data: batch_images}) / batch_idxs
                curr_L2_loss += self.L2_loss.eval({self.real_data: batch_images}) / batch_idxs

                # curr_avg_channel_diff = self.avg_channel_diff.eval({self.real_data: batch_images}) / batch_idxs
                
                curr_avg_channel_diff0 = self.avg_channel_diff0.eval({self.real_data: batch_images}) / batch_idxs
                curr_avg_channel_diff1 = self.avg_channel_diff1.eval({self.real_data: batch_images}) / batch_idxs
                curr_avg_channel_diff2 = self.avg_channel_diff2.eval({self.real_data: batch_images}) / batch_idxs

                curr_channel_std0 = self.channel_std0.eval({self.real_data: batch_images}) / batch_idxs
                curr_channel_std1 = self.channel_std1.eval({self.real_data: batch_images}) / batch_idxs

                curr_channel_std00 = curr_channel_std0[0]
                curr_channel_std01 = curr_channel_std0[1]
                curr_channel_std02 = curr_channel_std0[2]
                curr_channel_std10 = curr_channel_std1[0]
                curr_channel_std11 = curr_channel_std1[1]
                curr_channel_std12 = curr_channel_std1[2]

            g_losses += [curr_g_loss]
            base_g_losses += [curr_base_g_loss]
            latent_losses += [curr_latent_loss]
            ssim_losses += [curr_ssim_loss]
            L1_losses += [curr_L1_loss]
            L2_losses += [curr_L2_loss]

            avg_channel_diffs0 += [curr_avg_channel_diff0]
            avg_channel_diffs1 += [curr_avg_channel_diff1]
            avg_channel_diffs2 += [curr_avg_channel_diff2]

            channel_stds00 += [curr_channel_std00]
            channel_stds01 += [curr_channel_std01]
            channel_stds02 += [curr_channel_std02]
            channel_stds10 += [curr_channel_std00]
            channel_stds11 += [curr_channel_std01]
            channel_stds12 += [curr_channel_std02]

            if (epoch+1)%10 == 0:
                losses = np.transpose(np.array([g_losses, base_g_losses, latent_losses, ssim_losses, 
                L1_losses, L2_losses, avg_channel_diffs0, avg_channel_diffs1, avg_channel_diffs2,
                channel_stds00, channel_stds01, channel_stds02, channel_stds10, channel_stds11,
                channel_stds12]))

                # print losses
                np.savetxt("losses.csv", losses)

        losses = np.transpose(np.array([g_losses, base_g_losses, latent_losses, ssim_losses, 
            L1_losses, L2_losses, avg_channel_diffs0, avg_channel_diffs1, avg_channel_diffs2,
            channel_stds00, channel_stds01, channel_stds02, channel_stds10, channel_stds11,
            channel_stds12]))

        # print losses
        np.savetxt("losses.csv", losses)

    def discriminator(self, image, y=None, reuse=False):

        with tf.variable_scope("discriminator") as scope:

            # image is 256 x 256 x (input_c_dim + output_c_dim)
            if reuse:
                tf.get_variable_scope().reuse_variables()
            else:
                assert tf.get_variable_scope().reuse == False

            h0 = lrelu(conv2d(image, self.df_dim, name='d_h0_conv'))
            # h0 is (128 x 128 x self.df_dim)
            h1 = lrelu(self.d_bn1(conv2d(h0, self.df_dim*2, name='d_h1_conv')))
            # h1 is (64 x 64 x self.df_dim*2)
            h2 = lrelu(self.d_bn2(conv2d(h1, self.df_dim*4, name='d_h2_conv')))
            # h2 is (32x 32 x self.df_dim*4)
            h3 = lrelu(self.d_bn3(conv2d(h2, self.df_dim*8, d_h=1, d_w=1, name='d_h3_conv')))
            # h3 is (16 x 16 x self.df_dim*8)          
            h4 = linear(tf.reshape(h3, [h3.shape[0].value, -1]), 1, 'd_h3_lin')

            return tf.nn.sigmoid(h4), h4

    def generator(self, image, y=None):
        with tf.variable_scope("generator") as scope:


            s = self.output_size
            s2, s4, s8, s16, s32, s64, s128 = int(s/2), int(s/4), int(s/8), int(s/16), int(s/32), int(s/64), int(s/128)

            # image is (256 x 256 x input_c_dim)
            e1 = conv2d(image, self.gf_dim, name='g_e1_conv')
            # e1 is (128 x 128 x self.gf_dim)
            e2 = self.g_bn_e2(conv2d(lrelu(e1), self.gf_dim*2, name='g_e2_conv'))
            # e2 is (64 x 64 x self.gf_dim*2)
            e3 = self.g_bn_e3(conv2d(lrelu(e2), self.gf_dim*4, name='g_e3_conv'))
            # e3 is (32 x 32 x self.gf_dim*4)
            e4 = self.g_bn_e4(conv2d(lrelu(e3), self.gf_dim*8, name='g_e4_conv'))
            # e4 is (16 x 16 x self.gf_dim*8)
            e5 = self.g_bn_e5(conv2d(lrelu(e4), self.gf_dim*8, name='g_e5_conv'))
            # e5 is (8 x 8 x self.gf_dim*8)
            e6 = self.g_bn_e6(conv2d(lrelu(e5), self.gf_dim*8, name='g_e6_conv'))
            # e6 is (4 x 4 x self.gf_dim*8)
            e7 = self.g_bn_e7(conv2d(lrelu(e6), self.gf_dim*8, name='g_e7_conv'))
            # e7 is (2 x 2 x self.gf_dim*8)
            e8 = self.g_bn_e8(conv2d(lrelu(e7), self.gf_dim*8, name='g_e8_conv'))
            # e8 is (1 x 1 x self.gf_dim*8)

            # print "e8", e8.shape
            # noise = tf.random_uniform(e8.shape[:-1].as_list() + [1,])
            # e8_noisy =  tf.add(e8, noise)
            # # e8_noisy = tf.concat([e8, noise], 3)
            # print "e8 noisy", e8_noisy.shape
            e8_flat = tf.reshape(e8, (self.batch_size*2, -1))

            self.z_mu = linear(e8_flat, self.n_z, scope=None, stddev=0.02, bias_start=0.0, with_w=False, name='z_mu')
            self.z_sigma = linear(e8_flat, self.n_z, scope=None, stddev=0.02, bias_start=0.0, with_w=False, name='z_sigma')

            samples = tf.random_normal(shape=(self.batch_size*2, self.n_z), mean=0.0, stddev=1)
            z = self.z_mu + (samples*self.z_sigma)
            z = tf.expand_dims(z, 1)
            z = tf.expand_dims(z, 1)

            self.d1, self.d1_w, self.d1_b = deconv2d(tf.nn.relu(z),
                [self.batch_size*2, s128, s128, self.gf_dim*8], name='g_d1', with_w=True)
            d1 = tf.nn.dropout(self.g_bn_d1(self.d1), 0.5)
            d1 = tf.concat([d1, e7], 3)
            # d1 is (2 x 2 x self.gf_dim*8*2)

            self.d2, self.d2_w, self.d2_b = deconv2d(tf.nn.relu(d1),
                [self.batch_size*2, s64, s64, self.gf_dim*8], name='g_d2', with_w=True)
            d2 = tf.nn.dropout(self.g_bn_d2(self.d2), 0.5)
            d2 = tf.concat([d2, e6], 3)
            # d2 is (4 x 4 x self.gf_dim*8*2)

            self.d3, self.d3_w, self.d3_b = deconv2d(tf.nn.relu(d2),
                [self.batch_size*2, s32, s32, self.gf_dim*8], name='g_d3', with_w=True)
            d3 = tf.nn.dropout(self.g_bn_d3(self.d3), 0.5)
            d3 = tf.concat([d3, e5], 3)
            # d3 is (8 x 8 x self.gf_dim*8*2)

            self.d4, self.d4_w, self.d4_b = deconv2d(tf.nn.relu(d3),
                [self.batch_size*2, s16, s16, self.gf_dim*8], name='g_d4', with_w=True)
            d4 = self.g_bn_d4(self.d4)
            d4 = tf.concat([d4, e4], 3)
            # d4 is (16 x 16 x self.gf_dim*8*2)

            self.d5, self.d5_w, self.d5_b = deconv2d(tf.nn.relu(d4),
                [self.batch_size*2, s8, s8, self.gf_dim*4], name='g_d5', with_w=True)
            d5 = self.g_bn_d5(self.d5)
            d5 = tf.concat([d5, e3], 3)
            # d5 is (32 x 32 x self.gf_dim*4*2)

            self.d6, self.d6_w, self.d6_b = deconv2d(tf.nn.relu(d5),
                [self.batch_size*2, s4, s4, self.gf_dim*2], name='g_d6', with_w=True)
            d6 = self.g_bn_d6(self.d6)
            d6 = tf.concat([d6, e2], 3)
            # d6 is (64 x 64 x self.gf_dim*2*2)

            self.d7, self.d7_w, self.d7_b = deconv2d(tf.nn.relu(d6),
                [self.batch_size*2, s2, s2, self.gf_dim], name='g_d7', with_w=True)
            d7 = self.g_bn_d7(self.d7)
            d7 = tf.concat([d7, e1], 3)
            # d7 is (128 x 128 x self.gf_dim*1*2)

            self.d8, self.d8_w, self.d8_b = deconv2d(tf.nn.relu(d7),
                [self.batch_size*2, s, s, self.output_c_dim], name='g_d8', with_w=True)
            # d8 is (256 x 256 x output_c_dim)

            return tf.nn.tanh(self.d8)

    def sampler(self, image, y=None):

        with tf.variable_scope("generator") as scope:
            scope.reuse_variables()


            s = self.output_size
            s2, s4, s8, s16, s32, s64, s128 = int(s/2), int(s/4), int(s/8), int(s/16), int(s/32), int(s/64), int(s/128)

            # image is (256 x 256 x input_c_dim)
            e1 = conv2d(image, self.gf_dim, name='g_e1_conv')
            # e1 is (128 x 128 x self.gf_dim)
            e2 = self.g_bn_e2(conv2d(lrelu(e1), self.gf_dim*2, name='g_e2_conv'))
            # e2 is (64 x 64 x self.gf_dim*2)
            e3 = self.g_bn_e3(conv2d(lrelu(e2), self.gf_dim*4, name='g_e3_conv'))
            # e3 is (32 x 32 x self.gf_dim*4)
            e4 = self.g_bn_e4(conv2d(lrelu(e3), self.gf_dim*8, name='g_e4_conv'))
            # e4 is (16 x 16 x self.gf_dim*8)
            e5 = self.g_bn_e5(conv2d(lrelu(e4), self.gf_dim*8, name='g_e5_conv'))
            # e5 is (8 x 8 x self.gf_dim*8)
            e6 = self.g_bn_e6(conv2d(lrelu(e5), self.gf_dim*8, name='g_e6_conv'))
            # e6 is (4 x 4 x self.gf_dim*8)
            e7 = self.g_bn_e7(conv2d(lrelu(e6), self.gf_dim*8, name='g_e7_conv'))
            # e7 is (2 x 2 x self.gf_dim*8)
            e8 = self.g_bn_e8(conv2d(lrelu(e7), self.gf_dim*8, name='g_e8_conv'))
            # e8 is (1 x 1 x self.gf_dim*8)

            # noise = tf.random_uniform(e8.shape)
            # e8_noisy =  tf.add(e8, noise)
            e8_flat = tf.reshape(e8, (self.batch_size*2, -1))

            self.z_mu = linear(e8_flat, self.n_z, scope=None, stddev=0.02, bias_start=0.0, with_w=False, name='z_mu')
            self.z_sigma = linear(e8_flat, self.n_z, scope=None, stddev=0.02, bias_start=0.0, with_w=False, name='z_sigma')

            samples = tf.random_normal(shape=(self.batch_size*2, self.n_z), mean=0.0, stddev=1.0)
            z = self.z_mu + (samples*self.z_sigma)
            z = tf.expand_dims(z, 1)
            z = tf.expand_dims(z, 1)

            self.d1, self.d1_w, self.d1_b = deconv2d(tf.nn.relu(z),
                [self.batch_size*2, s128, s128, self.gf_dim*8], name='g_d1', with_w=True)
            d1 = tf.nn.dropout(self.g_bn_d1(self.d1), 0.5)
            d1 = tf.concat([d1, e7], 3)
            # d1 is (2 x 2 x self.gf_dim*8*2)

            self.d2, self.d2_w, self.d2_b = deconv2d(tf.nn.relu(d1),
                [self.batch_size*2, s64, s64, self.gf_dim*8], name='g_d2', with_w=True)
            d2 = tf.nn.dropout(self.g_bn_d2(self.d2), 0.5)
            d2 = tf.concat([d2, e6], 3)
            # d2 is (4 x 4 x self.gf_dim*8*2)

            self.d3, self.d3_w, self.d3_b = deconv2d(tf.nn.relu(d2),
                [self.batch_size*2, s32, s32, self.gf_dim*8], name='g_d3', with_w=True)
            d3 = tf.nn.dropout(self.g_bn_d3(self.d3), 0.5)
            d3 = tf.concat([d3, e5], 3)
            # d3 is (8 x 8 x self.gf_dim*8*2)

            self.d4, self.d4_w, self.d4_b = deconv2d(tf.nn.relu(d3),
                [self.batch_size*2, s16, s16, self.gf_dim*8], name='g_d4', with_w=True)
            d4 = self.g_bn_d4(self.d4)
            d4 = tf.concat([d4, e4], 3)
            # d4 is (16 x 16 x self.gf_dim*8*2)

            self.d5, self.d5_w, self.d5_b = deconv2d(tf.nn.relu(d4),
                [self.batch_size*2, s8, s8, self.gf_dim*4], name='g_d5', with_w=True)
            d5 = self.g_bn_d5(self.d5)
            d5 = tf.concat([d5, e3], 3)
            # d5 is (32 x 32 x self.gf_dim*4*2)

            self.d6, self.d6_w, self.d6_b = deconv2d(tf.nn.relu(d5),
                [self.batch_size*2, s4, s4, self.gf_dim*2], name='g_d6', with_w=True)
            d6 = self.g_bn_d6(self.d6)
            d6 = tf.concat([d6, e2], 3)
            # d6 is (64 x 64 x self.gf_dim*2*2)

            self.d7, self.d7_w, self.d7_b = deconv2d(tf.nn.relu(d6),
                [self.batch_size*2, s2, s2, self.gf_dim], name='g_d7', with_w=True)
            d7 = self.g_bn_d7(self.d7)
            d7 = tf.concat([d7, e1], 3)
            # d7 is (128 x 128 x self.gf_dim*1*2)

            self.d8, self.d8_w, self.d8_b = deconv2d(tf.nn.relu(d7),
                [self.batch_size*2, s, s, self.output_c_dim], name='g_d8', with_w=True)
            # d8 is (256 x 256 x output_c_dim)

            return tf.nn.tanh(self.d8)

    def _tf_fspecial_gauss(self, size, sigma):
        """Function to mimic the 'fspecial' gaussian MATLAB function
        """
        x_data, y_data = np.mgrid[-size//2 + 1:size//2 + 1, -size//2 + 1:size//2 + 1]

        x_data = np.expand_dims(x_data, axis=-1)
        x_data = np.expand_dims(x_data, axis=-1)
        x_data = np.repeat(x_data, 3, axis=2)

        y_data = np.expand_dims(y_data, axis=-1)
        y_data = np.expand_dims(y_data, axis=-1)
        y_data = np.repeat(y_data, 3, axis=2)

        x = tf.constant(x_data, dtype=tf.float32)
        y = tf.constant(y_data, dtype=tf.float32)

        g = tf.exp(-((x**2 + y**2)/(2.0*sigma**2)))
        return g / tf.reduce_sum(g)

    def tf_ssim(self, img1, img2, cs_map=False, mean_metric=True, size=31, sigma=9):
        img1 = (img1+1)/2
        img2 = (img2+1)/2
        window = self._tf_fspecial_gauss(size, sigma) # window shape [size, size]
        K1 = 0.01
        K2 = 0.03
        L = 1  # depth of image (255 in case the image has a differnt scale)
        C1 = (K1*L)**2
        C2 = (K2*L)**2
        mu1 = tf.nn.conv2d(img1, window, strides=[1,1,1,1], padding='VALID')
        mu2 = tf.nn.conv2d(img2, window, strides=[1,1,1,1],padding='VALID')
        mu1_sq = mu1*mu1
        mu2_sq = mu2*mu2
        mu1_mu2 = mu1*mu2
        sigma1_sq = tf.nn.conv2d(img1*img1, window, strides=[1,1,1,1],padding='VALID') - mu1_sq
        sigma2_sq = tf.nn.conv2d(img2*img2, window, strides=[1,1,1,1],padding='VALID') - mu2_sq
        sigma12 = tf.nn.conv2d(img1*img2, window, strides=[1,1,1,1],padding='VALID') - mu1_mu2
        if cs_map:
            value = (((2*mu1_mu2 + C1)*(2*sigma12 + C2))/((mu1_sq + mu2_sq + C1)*
                        (sigma1_sq + sigma2_sq + C2)),
                    (2.0*sigma12 + C2)/(sigma1_sq + sigma2_sq + C2))
        else:
            value = ((2*mu1_mu2 + C1)*(2*sigma12 + C2))/((mu1_sq + mu2_sq + C1)*
                        (sigma1_sq + sigma2_sq + C2))

        if mean_metric:
            value = tf.reduce_mean(value)
        return value


    def save(self, checkpoint_dir, step):
        model_name = "pix2pix.model"
        model_dir = "%s_%s_%s_%s" % (self.dataset_name, self.batch_size, self.output_size, self.test_name)
        checkpoint_dir = os.path.join(checkpoint_dir, model_dir)

        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        self.saver.save(self.sess,
                        os.path.join(checkpoint_dir, model_name),
                        global_step=step)

    def load(self, checkpoint_dir):
        if not checkpoint_dir:
            return False
        print(" [*] Reading checkpoint...")

        model_dir = "%s_%s_%s" % (self.dataset_name, self.batch_size, self.output_size)
        checkpoint_dir = os.path.join(checkpoint_dir, model_dir)

        ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
        if ckpt and ckpt.model_checkpoint_path:
            ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
            self.saver.restore(self.sess, os.path.join(checkpoint_dir, ckpt_name))
            return True
        else:
            return False

    def test(self, args):
        """Test pix2pix"""
        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)

        sample_files = glob('./datasets/{}/val/*.jpg'.format(self.dataset_name))

        # sort testing input
        n = [int(i) for i in map(lambda x: x.split('/')[-1].split('.jpg')[0], sample_files)]
        sample_files = [x for (y, x) in sorted(zip(n, sample_files))]

        # load testing input
        print("Loading testing images ...")
        sample = [load_data(sample_file, is_test=True) for sample_file in sample_files]

        if (self.is_grayscale):
            sample_images = np.array(sample).astype(np.float32)[:, :, :, None]
        else:
            sample_images = np.array(sample).astype(np.float32)

        sample_images = [sample_images[i:i+self.batch_size]
                         for i in xrange(0, len(sample_images), self.batch_size)]
        sample_images = np.array(sample_images)

        start_time = time.time()
        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")

        for i, sample_image in enumerate(sample_images):
            idx = i+1
            #print sample_image.shape
            # plt.imshow(sample_image[0][:,:,:3])
            # plt.show()
            # plt.imshow(sample_image[0][:,:,3:])
            # plt.show()
            samples = self.sess.run(
                self.fake_B_sample,
                feed_dict={self.real_data: sample_image}
            )
            save_images(samples, [self.batch_size*2, 1],
                        './{}/test_{:04d}.png'.format(args.test_dir, idx))
