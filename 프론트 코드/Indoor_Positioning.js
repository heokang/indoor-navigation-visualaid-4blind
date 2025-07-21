import React, { useState, useEffect, useRef } from 'react';
import {View, Text, Alert, StyleSheet, TouchableOpacity, Button, TouchableHighlight} from 'react-native';
import { Camera, CameraType } from 'expo-camera/legacy';
import { useNavigation } from '@react-navigation/native';
import BoldText from "./components/BoldText";
import NormalText from "./components/NormalText";
import Swipe_Button from "./components/Swipe_Button";
import { useWebSocket } from './WebSocketContext';
import { Audio } from 'expo-av';
import { playAudioFromBase64 } from './components/AudioHelper';




const Indoor_Positioning_Page  = () => {
  // const [ws1, setWs1] = useState(null);
  // const [ws2, setWs2] = useState(null);
  const [hasPermission, setHasPermission] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraRatio, setCameraRatio] = useState("4:3")
  // const [type, setType] = useState(Camera.Constants.Type.back);
  const cameraRef = useRef(null);
  const navigation = useNavigation();
  const [snapCount, setSnapCount] = useState(0);
  const [isNavigationComplete, setIsNavigationComplete] = useState(false);

  const {  websocket1 } = useWebSocket();


  // websocket
  useEffect(() => {
    websocket1.onmessage = (e) => {
      const message = JSON.parse(e.data);
      console.log('message:', message);
      if(message.message === 'audio_start') {
        playAudioFromBase64(message.audio_start_data);

      }
      if (message.message === 'activate_camera') {
        setCameraReady(true);
        playAudioFromBase64(message.audio_data);
      }
      if(message.message === 'photo_received') {

      }

      if (message.message === 'ips_success') {
        playAudioFromBase64(message.audio_ips_data);

        const start_point = message.start_point;
        const goal_point = message.goal_point;
        const polygon_points = message.polygon_points;
        console.log('StartPoint 체크:' ,start_point);
        console.log('GoalPoint 체크:',goal_point);
        console.log('PolygonPoint  체크:',polygon_points);




        setTimeout(() => {
           navigation.navigate('Route_Navigation');
          }, 2000);
        }

      if (message.message === 'ips_failed'){
        setIsNavigationComplete(false);
        setCameraReady(true);
        playAudioFromBase64(message.audio_fail_data);
      }

    }

    // websocket1.onclose = (e) => {
    //     console.log('winter Disconnected');
    //   };
    // websocket1.onerror = (err) => {
    //     setTimeout(() => {
    //       connect();
    //     }, 2000 ); // 2초 후 재연결 시도
    //   };


    // websocket.onmessage = (e) => {
    //   const message_path = JSON.parse(e.data);
    //   console.log(message_path);
    // }
    // websocket2.onclose = (e) => {
    //     console.log('ws2 Disconnected');
    //   };
    // websocket2.onerror = (err) => {
    //     setTimeout(() => {
    //       connect();
    //     }, 1000 ); // 2초 후 재연결 시도
    //   };

    // setWs1(websocket1);
    // setWs2(websocket2);

    return () => {
      // websocket1.close();
      // websocket2.close();
    };
  }, []);

  //카메라 권한요청
    useEffect(() => {
        (async () => {
            const { status } = await Camera.requestCameraPermissionsAsync();
            setHasPermission(status === 'granted');
        })();
    }, []);


  // 카메라 접근 권한이 없는 경우의 처리
    if (hasPermission === null) {
      return <View style={styles.container}><Text>Requesting for camera permission...</Text></View>;
    }
    if (hasPermission === false) {
      return <View style={styles.container}><Text>No access to camera</Text></View>;
    }


  const handlePress = () => {
    if (websocket1) {
      websocket1.send(JSON.stringify({ message: 'activate_camera' }));
    }
  };

// 카메라 작동 및 서버로 사진 보내기
  const handleSnap = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync({ base64: true });
        const base64Image = `data:image/jpeg;base64,${photo.base64}`;

        if (websocket1 && websocket1.readyState === WebSocket.OPEN) {
          console.log("Photo sent to server: " + base64Image.substring(0, 30) + "...");
          websocket1.send(JSON.stringify({ image: base64Image }));

          // snapCount 상태를 업데이트합니다.
          setSnapCount(prevCount => {
            const updatedCount = prevCount + 1;

            // 만약 사진이 3장 촬영되었다면 calculate_position 메시지를 보냅니다.
            if (updatedCount === 4) {
              setIsNavigationComplete(true);
              setTimeout(() => {
              websocket1.send(JSON.stringify({ message: 'calculate_position' }));
              console.log("Send Calculate_Position after 5seconds");
            }, 5000);
            return 0; // 카운트를 초기화합니다.
            }
            return updatedCount; // 업데이트된 카운트 값을 반환합니다.
          });
        } else {
          console.error("WebSocket is not open. Ready state:", websocket1.readyState);
        }
      } catch (error) {
        console.error("Error taking picture or sending:", error);
      }
    } else {
      console.error("Camera reference is not available.");
    }
  };

// function playAudioFromBase64(base64String) {
//   // Base64를 바이트 문자열로 디코딩
//   const audioArray = Buffer.from(base64String, 'base64');
//
//   const audioBlob = new Blob([audioArray.buffer], { type: 'audio/wav' });
//   const audioUrl = URL.createObjectURL(audioBlob);
//
//   const audio = new Audio(audioUrl);
//   audio.play()
//     .then(() => console.log('음성 안내를 시작합니다.'))
//     .catch(error => console.error('음성 안내 재생에 실패했습니다.', error));
// }

  if (isNavigationComplete) {
  // 네비게이션이 완료된 후 보여줄 컴포넌트 또는 UI
    return (
      <View style={styles.containercenter}>
        <BoldText style={styles.centeredText}>실내측위 진행중</BoldText>
      </View>);
  }

  // 카메라 활성화 시 UI
  if (cameraReady) {
    return (
      <Camera
        style={{ flex: 1 }}
        type={Camera.Constants.Type.back}
        ref={cameraRef}
        ratio={cameraRatio}>
        <TouchableOpacity
          style={{ flex: 1 }}
          onPress={handleSnap}
          activeOpacity={1.0}>
          {/* Camera overlay content here */}
          <View style={styles.cameraOverlay}>
            {/* Any overlay content such as buttons or text */}
          </View>
        </TouchableOpacity>
      </Camera>
    );
  }

  // 카메라 비활성화 시 UI
  return (
    <View style={styles.container}>
      <View style={styles.White_Section}>
        <NormalText>
          길찾기를 위한 현재 위치 인식을 시작하겠습니다.{'\n'}아래 길찾기 버튼을 위로 올려주세요.
        </NormalText>
      </View>
      <TouchableHighlight
          underlayColor="#FFCC00"
          onPress={handlePress}>
          <View style={styles.buttonStyle}>
            <BoldText>길찾기</BoldText>
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
  containercenter: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center', // This aligns children vertically in the center
    alignItems: 'center',     // This aligns children horizontally in the center
  },
  centeredText: {
    fontSize: 24,             // Set the font size if needed
    fontWeight: 'bold',
    textAlign: 'center',      // Ensure text is centered in the Text component
  },
  Yello_Section: {
    backgroundColor: '#FFD600', // 상단 섹션에 노란색 배경 적용
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 60,
    paddingBottom: 60,
    borderRadius: 30,
    flex: 4,
  },
  title: {
    color: 'blue',
    fontSize: 50,
    fontWeight: 'bold',
  },
  White_Section: {
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingBottom: 100, // 버튼과 하단 가장자리 사이의 여백
    flex: 3,
  },
  button: {
    backgroundColor: '#FFD600',
    paddingHorizontal: 50,
    paddingVertical: 30,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 1.41,
    elevation: 2,
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

export default Indoor_Positioning_Page;