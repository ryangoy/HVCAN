# echo Starting baseline test
# python main.py --test_name=baseline --epoch=30 --sample_dir=baseline_samples --L1_lambda=100 --latent_lambda=1.0 --ssim_lambda=1.0
# echo Starting l1=10 test
# python main.py --test_name=l1_10 --epoch=30 --sample_dir=low_l1_samples --L1_lambda=10 --latent_lambda=1.0 --ssim_lambda=1.0
# echo Starting ssim=10 test
# python main.py --test_name=ssim_10 --epoch=30 --sample_dir=high_ssim_samples --L1_lambda=100 --latent_lambda=1.0 --ssim_lambda=10.0
# echo Starting latent_lambda=10 test
# python main.py --test_name=latent_lambda_10 --epoch=30 --sample_dir=high_latent_lambda --L1_lambda=100 --latent_lambda=10.0 --ssim_lambda=1.0
# echo Starting latent_lambda=10 and ssim=10 test
# python main.py --test_name=ssim_10_latent_lambda_10 --epoch=30 --sample_dir=high_latent_lambda_high_ssim --L1_lambda=100 --latent_lambda=10.0 --ssim_lambda=1.0
# echo Starting ssim=100 test
# python main.py --test_name=ssim_100 --epoch=30 --sample_dir=higher_ssim --L1_lambda=100 --latent_lambda=1.0 --ssim_lambda=100.0
# echo Starting l1=10 and latent_lambda=10 and ssim=10 test
# python main.py --test_name=l1_10_ssim_10_latent_lambda_10 --epoch=30 --sample_dir=low_l1_high_latent_lambda_high_ssim --L1_lambda=10 --latent_lambda=10.0 --ssim_lambda=1.0
# echo Starting ssim=10 quick test
# python main.py --test_name=ssim_10_quick --epoch=2 --sample_dir=high_ssim_quick --L1_lambda=100 --latent_lambda=1.0 --ssim_lambda=10.0
# echo Starting ssim=10 long latent=.1 test
# python main.py --test_name=ssim_10_latent_e-1 --epoch=100 --sample_dir=high_ssim_long_low_latent --L1_lambda=100 --latent_lambda=.1 --ssim_lambda=10.0
echo Starting ssim=10 long test
python main.py --test_name=ssim_10_long8 --batch_size=1 --epoch=100 --sample_dir=high_ssim_long8 --L1_lambda=100 --latent_lambda=1.0 --ssim_lambda=10.0






# just switching l1_lambda to 10 does not work, diverges and d_loss goes to 0 quickly and stays
