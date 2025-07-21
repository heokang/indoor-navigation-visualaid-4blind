import React, { useEffect, useState , useRef} from 'react';
import {StyleSheet, Button,Text, TouchableHighlight, View} from 'react-native';
import BoldText from "./components/BoldText";
import NormalText from "./components/NormalText";
import {useWebSocket} from "./WebSocketContext";
import {Audio} from "expo-av";
import * as FileSystem from 'expo-file-system';
import {playAudioFromBase64} from "./components/AudioHelper";
import Route_Guidance from "./Route_Guidance";
import {Camera} from "expo-camera";
import {Magnetometer} from "expo-sensors";


const Route_Navigation_Page = ({ navigation }) => {
  const { websocket1 } = useWebSocket();
  const [recording, setRecording] = useState(false);
  const [permissionResponse, requestPermission] = Audio.usePermissions();
  const [firstSensor, setFirstSensor] = useState(false);
  const firstsensorDataRef = useRef(firstSensor);

// 레코딩 옵션 정의
  const recordingOptions = {
    android: {
      extension: '.mp3',
      outputFormat: Audio.RECORDING_OPTION_ANDROID_OUTPUT_FORMAT_MPEG_4,
      audioEncoder: Audio.RECORDING_OPTION_ANDROID_AUDIO_ENCODER_AAC,
      sampleRate: 44100,
      numberOfChannels: 2,
      bitRate: 128000,
    },
    ios: {
      extension: '.caf',
      audioQuality: Audio.RECORDING_OPTION_IOS_AUDIO_QUALITY_MAX,
      sampleRate: 44100,
      numberOfChannels: 2,
      bitRate: 128000,
      linearPCMBitDepth: 16,
      linearPCMIsBigEndian: false,
      linearPCMIsFloat: false,
    },
  };

  useEffect(() => {
    websocket1.onmessage = (e) => {
      const message = JSON.parse(e.data);
      console.log('message:', message);


      if(message.message === 'set_destination'){

        websocket1.send(JSON.stringify({ type: 'start_path_finding'}));
        console.log('Send Start_path_finding');
        playAudioFromBase64(message.audio_data);
        // console.log('Send Prepare_positioning');
        // websocket1.send(JSON.stringify({ type: 'prepare_positioning'}));
        setTimeout(() => {
          navigation.navigate('Route_Guidance');}, 2000);
        console.log('Route_Guidance');
      }

      else if(message.message === 'fail_set_destination'){
        playAudioFromBase64(message.audio_data);
      }

        };
    }, [websocket1]);

// 녹음 권한요청
  useEffect(() => {
      (async () => {
            if (permissionResponse === null || permissionResponse.status !== 'granted') {
              console.log('Requesting permission..');
              await requestPermission();
            }
          })();
  }, [permissionResponse]);

  useEffect(() => {
      firstsensorDataRef.current = firstSensor;
  }, [firstSensor]);


// 지자기 센서값 보내기
  useEffect(() => {
    console.log('FirstSensor: ', firstSensor);
    if(firstsensorDataRef.current==false){ // sensorDataRef.current가 false일 때만 실행
      let magnetometerSubscription = Magnetometer.addListener(data => {
        const magnetometerData = {
          time: new Date().toISOString(),
          x1: data.x,
          y1: data.y,
          z1: data.z,
        };

        const sensorData = { magnetometerData };
        console.log('Sending First Magnetometer:', JSON.stringify({ type: 'start_set_first', sensorData }));
        websocket1.send(JSON.stringify({ type: 'start_set_first', sensorData }));

    });
      return () => {
        if (magnetometerSubscription) {
          magnetometerSubscription.remove();
        }
      };
    }
  }, [websocket1,firstsensorDataRef.current]);

//녹음 시작
  const startRecording = async () => {
    if (permissionResponse.status !== 'granted') {
      console.log('Requesting permission..');
      await requestPermission();
    }
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      console.log('Starting recording..');
      const { recording } = await Audio.Recording.createAsync(recordingOptions);
      setRecording(recording);
      setFirstSensor(true);
      console.log('Recording started');
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };

//녹음 종료 및 서버 전송
  const stopRecording = async () => {
    if (recording) {
      try {
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI(); // 파일 URI를 얻습니다.
        console.log('Recording stopped and stored at', uri);
        setRecording(undefined);

          // 파일을 base64 인코딩된 문자열로 읽어옵니다.
        const base64Audio = await FileSystem.readAsStringAsync(uri, { encoding: FileSystem.EncodingType.Base64 });
        const base64AudioString = `data:audio/mp3;base64,${base64Audio}`;

        websocket1.send(JSON.stringify({ message: 'destination', audio: base64AudioString }));
        console.log("Audio sent to server: " + base64AudioString.substring(0, 30) + "...");
      } catch (error) {
        console.error('Error stopping and reading recording:', error);
      }
    } else {
      console.error('Recording is not active.');
    }
  };


  return (
    <View style={styles.container}>
      <View style={styles.bottomSection}>
        <NormalText>목적지 버튼을 누르고 {'\n'}목적지를 말해주세요</NormalText>
      </View>
      <TouchableHighlight
          style={styles.topSection}
          underlayColor="#FFCC00"
          onPressIn={startRecording}
          onPressOut={stopRecording}>
        <View >
            <BoldText>목적지</BoldText>
        </View>
      </TouchableHighlight>

    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  topSection: {
    backgroundColor: '#FFD600',
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 60,
    paddingBottom: 60,
    borderRadius: 30,
    flex: 4,
  },
  bottomSection: {
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingBottom: 100,
    flex: 3,
  },
});

export default Route_Navigation_Page;