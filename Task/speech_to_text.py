import os
# библиотека для распознавания речи
import speech_recognition as sr
import io
import soundfile as sf
import tempfile

# Преобразование аудиофайла wav в текст, для последующей отправки чату gpt
def speech_to_text(path_to_wav):
    # Создаем объект распознавателя речи
    r = sr.Recognizer()
    #  Загружаем аудио файл
    hellow=sr.AudioFile(path_to_wav)
    # Распознаем речь из аудио файла
    with hellow as source:
        audio = r.record(source)
    try:
        #  вызывает API Sphinx для распознавания речи на русском языке
        s = r.recognize_sphinx(audio, language='ru-RU')
        resutl = s
        os.remove(path_to_wav)
        return resutl
    except Exception as e:
        print(e)
        os.remove(path_to_wav)
        return 0



def ogg2wav(ogg: bytes):
    # io.BytesIO это файл, но существует только в памяти нашей программы. Это означает, что вы можете читать и писать
    # в него, как в файл, но без создания каких-либо реальных файлов на диске.
    # Присваиваем переменной область буфера байтов (по факту это содержимое аудио файла, представленного в байтах)
    ogg_buf = io.BytesIO(ogg)
    # Даем ей название
    ogg_buf.name = 'file.ogg'
    # soundfile.read возвращает кортеж из двух элементов: первый — массив со всеми данными, считанными из файла,
    # второй — частота дискретизации в выборках в секунду
    data, samplerate = sf.read(ogg_buf)
    # присваиваем переменной некую область буфера байтов
    wav_buf = io.BytesIO()
    # Даем ей название
    wav_buf.name = 'file.wav'
    # Записываем в file.wav аудиофайл
    sf.write(wav_buf, data, samplerate)
    wav_buf.seek(0)  # Necessary for `.read()` to return all bytes
    path_to_wav = r'C:\Users\Public\PycharmProj\TG_BOT\Task\temp\temp_wav.wav'
    with open(path_to_wav, 'wb') as file_obj:
        file_obj.write(wav_buf.getbuffer())
    return path_to_wav

# Преобразуем формат записанного аудиофайла ogg в текст
def ogg_to_text(ogg: bytes):
    # Конвертируем в формат wav
    wav_buf = ogg2wav(ogg)
    result = speech_to_text(wav_buf)
    if result == 0:
        return "Не удалось преобразовать аудио в текст!"
    else:
        return result