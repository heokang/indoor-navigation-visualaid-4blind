import React, { useState, useEffect , useRef }from 'react';
import {View, Text, StyleSheet, TouchableOpacity, Image, Alert, TouchableHighlight} from 'react-native';
import { Accelerometer,  Gyroscope, Magnetometer, DeviceMotion} from 'expo-sensors';
import { useWebSocket } from './WebSocketContext';
import BoldText from "./components/BoldText";
import Swipe_Button from "./components/Swipe_Button";
import { playAudioFromBase64 } from './components/AudioHelper';
import { useNavigation, useIsFocused } from '@react-navigation/native';


const Route_Guidance_Page = ({ navigation }) => {
  const { websocket1 } = useWebSocket();
  const [statusMessage, setStatusMessage] = useState('경로 안내중');
  const isFocused = useIsFocused();
  const [ sensorData , setsensorData ] = useState(false);
  const [ isCollecting, setIsCollecting] = useState(false);
  const sensorDataRef = useRef(sensorData);
  const audioPlayedRef = useRef(false);
  const prepareaudioRef = useRef(false);

// 웹소켓
  useEffect(() => {
    websocket1.onmessage = (e) => {
      const message = JSON.parse(e.data);
      if (!message.audio_data)(
          console.log('message:', message)
      )


      if (message.message === 'start_set_position' && !sensorData) {
        setIsCollecting(true);
        if(!prepareaudioRef.current){
          setTimeout(() => {
          playAudioFromBase64(message.audio_data);
        }, 500);

          prepareaudioRef.current = true;
        }
      }

      if (message.message === 'start_set_position' && sensorDataRef.current == true) {
        setsensorData(false);
        setIsCollecting(true);
        audioPlayedRef.current = false;
      }

      else if (message.message === 'finish_set_position' && !sensorData) {
        setsensorData(true);
        setIsCollecting(true);
        setStatusMessage('경로 안내중');
        if(!audioPlayedRef.current){
          playAudioFromBase64(message.audio_finish_data);
          audioPlayedRef.current = true;
        }
        // websocket1.send(JSON.stringify({ message: 'finish_set_position' })); // DB 지우는거
      }

      else if (message.message === 'direction_deviation') {
        setStatusMessage('방향이탈');
        console.log('이탈');
        playAudioFromBase64(message.audio_dev_data);
        // websocket1.send(JSON.stringify({ type: 'prepare_positioning'}));
        prepareaudioRef.current = false;
      }

      // else if (message.message === 'continue_navigation'){
      //   setStatusMessage('경로 안내중');
      //   playAudioFromBase64(message.audio_data);
      // }

      else if (message.message === 'turn_alert') {
        const newDirectionText = `${message.new_direction} 시 방향전환`;
        setStatusMessage(newDirectionText);
        console.log(`${newDirectionText} 전환`);
        playAudioFromBase64(message.audio_change_data);
        setTimeout(() => {
          setStatusMessage('경로 안내중');
        }, 2000);
      }

      else if (message.message === 'navigation_completed') {
        setStatusMessage('도착');
        console.log('완료');
        playAudioFromBase64(message.audio_fin_data);
        websocket1.send(JSON.stringify({ message: 'finish' }));
        console.log('Send Finish');
        setTimeout(() => {
          navigation.navigate('Winter');
        }, 2000);
        console.log('Return_Start');
        // websocket.close()
        websocket1.close()
      }
    };
  }, [websocket1]);


// sensorData 상태 변화 감지 및 적용
  useEffect(() => {
      sensorDataRef.current = sensorData;
  }, [sensorData]);

// 화면 바뀌면 prepare_positioning 보내기
  useEffect(() => {
    if (isFocused) {
      websocket1.send(JSON.stringify({ type: 'prepare_positioning'}));
      console.log('Prepare Positioning Sent');
    }}, [isFocused, websocket1]);

// 지자기 센서값 보내기
  useEffect(() => {
    if (isCollecting && sensorDataRef.current == false) { // sensorDataRef.current가 false일 때만 실행
      let magnetometerSubscription = Magnetometer.addListener(data => {
        const magnetometerData = {
          time: new Date().toISOString(),
          x1: data.x,
          y1: data.y,
          z1: data.z,
        };

      // 웹소켓 상태를 확인하고 준비되어 있으면 바로 데이터를 전송합니다.

        const sensorData = { magnetometerData };
        console.log('Mag변경적용: ', sensorDataRef.current);
        console.log('Sending Magnetometer:', JSON.stringify({ type: 'start_set_position', sensorData }));
        websocket1.send(JSON.stringify({ type: 'start_set_position', sensorData }));

    });

      return () => {
        if (magnetometerSubscription) {
          magnetometerSubscription.remove();
        }
      };
    }
  }, [websocket1, isCollecting, sensorData]);

// 센서값 보내는 부분
  useEffect(() => {
    let devicemotionSubscription = null;
    let magnetometerSubscription = null;
    let intervalId = null;
    let sensorDataBuffer = [];

    if (isCollecting && sensorDataRef.current==true) {
      // 센서값 가져오는 업데이트 주기 설정
      DeviceMotion.setUpdateInterval(100);
      Magnetometer.setUpdateInterval(100);

      // DeviceMotion 데이터 구독
      devicemotionSubscription = DeviceMotion.addListener(data => {
        if (data && data.acceleration) {
          const deviceMotionData = {
            sensorType: 'DeviceMotion',
            timestamp: Math.floor(Date.now()),
            x: data.acceleration.x,
            y: data.acceleration.y,
            z: data.acceleration.z,
          };
          sensorDataBuffer.push({ deviceMotionData });
        }
      });

      // Magnetometer 데이터 구독
      magnetometerSubscription = Magnetometer.addListener(data => {
        const magnetometerData = {
          sensorType: 'Magnetometer',
          timestamp: Math.floor(Date.now()),
          x1: data.x,
          y1: data.y,
          z1: data.z,
        };
        sensorDataBuffer.push({ magnetometerData });
      });

      // 주기적으로 센서 데이터를 서버로 전송
       const intervalId = setInterval(() => {
          if (websocket1.readyState === WebSocket.OPEN && sensorDataBuffer.length > 0) {
            const deviceMotionEntry = sensorDataBuffer.find(entry => entry.deviceMotionData !== undefined);
            const magnetometerEntry = sensorDataBuffer.find(entry => entry.magnetometerData !== undefined);
            const deviceMotionData = deviceMotionEntry ? deviceMotionEntry.deviceMotionData : undefined;
            const magnetometerData = magnetometerEntry ? magnetometerEntry.magnetometerData : undefined;

            if (deviceMotionData && magnetometerData && isCollecting) {
              const timeDiff = Math.abs(deviceMotionData.timestamp - magnetometerData.timestamp);
              if(timeDiff <= 70){
                const combinedData = {
                type:  'sensor_data',
                sensorData: {
                  time: new Date(deviceMotionData.timestamp).toISOString(), // 두 센서의 timestamp가 같다고 가정
                  x: deviceMotionData.x,
                  y: deviceMotionData.y,
                  z: deviceMotionData.z,
                  x1: magnetometerData.x1,
                  y1: magnetometerData.y1,
                  z1: magnetometerData.z1
             }
              };
                console.log('Sen변경적용: ',sensorDataRef.current);
                console.log('Sending Data:', JSON.stringify(combinedData));
                websocket1.send(JSON.stringify(combinedData));
              }

            } else {}}
          else {}
          sensorDataBuffer = [];
        }, 100);
    }

    // 정리(cleanup) 함수
    return () => {
      if (devicemotionSubscription) devicemotionSubscription.remove();
      if (magnetometerSubscription) magnetometerSubscription.remove();
      if (intervalId) clearInterval(intervalId);
    };
  }, [websocket1, isCollecting, sensorData]);


// 안내종료 버튼을 내리면 실행되는 변수
  const _end = () => {
    websocket1.send(JSON.stringify({ message: 'finish' }));
    console.log('Send Finish');
    navigation.navigate('Winter');
    console.log('Return_Start');
    // websocket.close()
    websocket1.close()
  };


  return (
    <View>
      <TouchableHighlight
          underlayColor="#FFCC00"
          onPress={_end}>
          <View style={styles.buttonStyle}>
            <BoldText>안내종료</BoldText>
          </View>
      </TouchableHighlight>
      <View style={styles.statusMessageContainer}>
        <BoldText style={styles.dynamicValue}>
        {statusMessage}
        </BoldText>
      </View>
    </View>
  );
  };



const styles = StyleSheet.create({
  container: {
    flex: 3,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  dynamicValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'black',
    padding: 10,
    textAlign: 'center',
  },
  statusMessageContainer: {
    paddingVertical: 110,
    paddingHorizontal: 10,
    alignItems: 'center',
  },
  buttonStyle: {
    backgroundColor: '#FFD600', // 노란색 배경
    paddingVertical: 120,
    paddingHorizontal: 40,
    alignItems: 'center', // 내용 중앙 정렬
    justifyContent: 'center',
    elevation: 3, // 안드로이드용 그림자
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 3,
  },
});

export default Route_Guidance_Page;