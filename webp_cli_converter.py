import os
from PIL import Image

def convert_images_to_webp(input_folder, output_folder=None, quality=80, lossless=False):
    """
    تبدیل تصاویر PNG و JPG در پوشه ورودی به فرمت WebP و ذخیره آن‌ها
    در پوشه خروجی (یا پوشه ورودی اگر output_folder مشخص نشده باشد).

    آرگومان‌ها:
        input_folder (str): مسیر پوشه حاوی تصاویر PNG و JPG.
        output_folder (str, optional): مسیر پوشه‌ای که تصاویر WebP در آن ذخیره می‌شوند.
                                       اگر None باشد، تصاویر WebP در پوشه ورودی ذخیره می‌شوند.
        quality (int, optional): سطح کیفیت برای فشرده‌سازی WebP با اتلاف (0-100). پیش‌فرض 80.
        lossless (bool, optional): استفاده از فشرده‌سازی WebP بدون اتلاف. پیش‌فرض False (با اتلاف).
    """

    if not os.path.isdir(input_folder):
        print(f"خطا: پوشه ورودی '{input_folder}' وجود ندارد یا یک دایرکتوری نیست.")
        return

    if output_folder is None:
        output_folder = input_folder  # ذخیره در همان پوشه به صورت پیش‌فرض

    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)  # ایجاد پوشه خروجی اگر وجود نداشته باشد

    if not 0 <= quality <= 100:
        print("خطا: کیفیت باید بین 0 و 100 باشد. از کیفیت پیش‌فرض 80 استفاده می‌شود.")
        quality = 80

    image_files_found = False
    valid_extensions = {'.png', '.jpg', '.jpeg'} # استفاده از مجموعه برای جستجوی سریع‌تر

    for filename in os.listdir(input_folder):
        if os.path.isfile(os.path.join(input_folder, filename)):
            if os.path.splitext(filename.lower())[1] in valid_extensions:
                image_files_found = True
                input_filepath = os.path.join(input_folder, filename)
                try:
                    img = Image.open(input_filepath)
                    base_filename, ext = os.path.splitext(filename)
                    output_webp_filename = base_filename + ".webp"
                    output_webp_filepath = os.path.join(output_folder, output_webp_filename)

                    print(f"در حال تبدیل: {filename} به {output_webp_filename}\n")

                    img.save(output_webp_filepath, 'webp', quality=quality, lossless=lossless)

                    print(f"ذخیره شد: {output_webp_filename}\n")

                except Exception as e:
                    print(f"خطا در پردازش {filename}: {e}")

    if not image_files_found:
        print("هیچ تصویر PNG یا JPG در پوشه ورودی یافت نشد.")
    else:
        print("تبدیل کامل شد!")


if __name__ == "__main__":
    input_directory = input("مسیر پوشه ورودی حاوی تصاویر را وارد کنید: ")
    output_directory = input("مسیر پوشه خروجی را وارد کنید (برای ذخیره در پوشه ورودی، خالی بگذارید): ") or None # امکان خالی گذاشتن برای همان پوشه

    while True:
        quality_input = input("کیفیت WebP را وارد کنید (0-100، پیش‌فرض 80): ") or "80" # امکان استفاده از پیش‌فرض در صورت خالی گذاشتن
        try:
            quality_level = int(quality_input)
            break  # خروج از حلقه در صورت موفقیت‌آمیز بودن تبدیل به عدد صحیح
        except ValueError:
            print("ورودی نامعتبر. لطفاً یک عدد صحیح بین 0 و 100 وارد کنید.")

    lossless_input = input("آیا از فشرده‌سازی WebP بدون اتلاف استفاده شود؟ (بله/خیر، پیش‌فرض خیر): ").lower()
    use_lossless = lossless_input in ('بله', 'yes', 'y', 'true') # پذیرش 'بله'، 'y' و 'true'

    convert_images_to_webp(input_directory, output_directory, quality=quality_level, lossless=use_lossless)
