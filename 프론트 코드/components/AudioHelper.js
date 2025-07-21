import {Audio} from "expo-av";

export async function playAudioFromBase64(base64String) {
  try {
    const { sound } = await Audio.Sound.createAsync(
      { uri: `data:audio/wav;base64,${base64String}` },
      { shouldPlay: true }
    );

    await sound.playAsync();
    console.log('음성 안내를 시작합니다.');

    sound.setOnPlaybackStatusUpdate(async (status) => {
      if (status.didJustFinish) {
        await sound.unloadAsync();
      }
    });
  } catch (error) {
    console.error('음성 안내 재생에 실패했습니다.', error);
  }
}

