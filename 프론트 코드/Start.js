import React, {useState, useEffect, useRef} from 'react';
import { StyleSheet, Text, View, TouchableHighlight, Alert, Button } from 'react-native';
import BoldText from "./components/BoldText";
import * as Location from 'expo-location';
import { useWebSocket } from './WebSocketContext';
import { playAudioFromBase64 } from './components/AudioHelper';
import Route_Guidance from "./Route_Guidance";
import * as Camera from 'expo-camera';
import {Audio} from "expo-av";
import {DeviceMotion, Magnetometer} from "expo-sensors";
// import * as Updates from 'expo-updates';


const Start = ({ navigation }) => {
  const [collectingGPS, setCollectingGPS] = useState(false);
  const [locationPermission, setLocationPermission] = useState(false);
  const { websocket1 } = useWebSocket();
  const [ websocket, setWs] = useState(null);
  const [hasPermission, setHasPermission] = useState(null);
  const [permissionResponse, requestPermission] = Audio.usePermissions();
  const collectingGPSRef = useRef(collectingGPS);


// 웹소켓
  useEffect(() => {
      const connect = () => {
        const ws = new WebSocket(`ws://220.67.127.145:8000/ws/w_inter/gps`)
          ws.onopen = () => {
              console.log('gps Connected');
          };
          ws.onclose = () => {
              console.log('gps Disconnected');
          };
          ws.onerror = (err) => {
              console.error('WebSocket Error:', err);
          };
          setWs(ws)
      };

      if (locationPermission && collectingGPS) {
          connect();
      }

      // if (collectingGPSRef.current == true) {
      //     connect();
      // }
      else {
          if (websocket) {
          }
      }

      return () => {
      };
      }, [collectingGPS]);

// GPS 권한 요청
  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      setLocationPermission(status === 'granted');
    })();
  }, []);



// 녹음 권한요청
  useEffect(() => {
      (async () => {
            if (permissionResponse === null || permissionResponse.status !== 'granted') {
              console.log('Requesting permission..');
              await requestPermission();
            }
          })();
  }, [permissionResponse]);

// GPS 수집 및 서버 전송
  useEffect(() => {
      const handleGetLocation = async () => {
          if (websocket && websocket.readyState === WebSocket.OPEN && collectingGPS) {
              try {
                  let currentLocation = await Location.getCurrentPositionAsync({accuracy: Location.Accuracy.Highest});
                  const locationData = {
                      type: "location",
                      timestamp: Math.floor(Date.now() / 1000),
                      latitude: currentLocation.coords.latitude,
                      longitude: currentLocation.coords.longitude,
                  };
                  websocket.send(JSON.stringify(locationData));
                  console.log("Location datat:", locationData);
              } catch (error) {
                  console.error("Failed to send location data:", error);
              }
          } else {
              console.error("WebSocket is not open or does not exist.");
          }
      };

      let intervalId;
      if (locationPermission && collectingGPS) {
          intervalId = setInterval(handleGetLocation, 10000);
      }
      return () => {
          if (intervalId) clearInterval(intervalId);

      };}, [collectingGPS, websocket]);

    // useEffect(() => {
    //   const handleGetLocation = async () => {
    //       if (websocket && collectingGPS) {
    //           try {
    //             let devicemotionSubscription = DeviceMotion.addListener(data => {
    //               const deviceMotionData = {
    //                 time: new Date().toISOString(),
    //                 x: data.acceleration.x,
    //                 y: data.acceleration.y,
    //                 z: data.acceleration.z,
    //               };
    //
    //             // 웹소켓 상태를 확인하고 준비되어 있으면 바로 데이터를 전송합니다.
    //
    //               const sensorData = { deviceMotionData };
    //               console.log('Sending Magnetometer:', JSON.stringify({ type: 'location', sensorData }));
    //               websocket.send(JSON.stringify({ type: 'location', sensorData }));
    //
    //           });
    //
    //           } catch (error) {
    //               console.error("Failed to send location data:", error);
    //           }
    //       } else {
    //           console.error("WebSocket is not open or does not exist.");
    //       }
    //   };
    //
    //   let intervalId;
    //   if (locationPermission && collectingGPS) {
    //       intervalId = setInterval(handleGetLocation, 100);
    //   }
    //   return () => {
    //       if (intervalId) clearInterval(intervalId);
    //     //   if (devicemotionSubscription) {
    //     //   devicemotionSubscription.remove();
    //     // }
    //
    //   };}, [collectingGPS, websocket]);


//   async function checkForAndApplyUpdates() {
//     try {
//         const update = await Updates.checkForUpdateAsync();
//         if (update.isAvailable) {
//             await Updates.fetchUpdateAsync();
//             // 업데이트가 있을 경우 로그 남기기나 사용자에게 알림
//             console.log('New update downloaded.');
//             // 업데이트 적용
//             Updates.reloadAsync();
//         } else {
//             console.log('No new updates found.');
//         }
//     } catch (error) {
//         console.error('Error checking for app updates:', error);
//     }
// }


  const toggleGPS = () => {
    setCollectingGPS(!collectingGPS);
  };

  const _IndoorPositioning = () => {
    navigation.navigate('Indoor_Positioning');
    websocket1.send(JSON.stringify({ message: 'start' }));
  };


  return (
    <View style={styles.container}>
      <TouchableHighlight
          underlayColor="#FFCC00"
          onPress={_IndoorPositioning}>
          <View style={styles.buttonStyle}>
            <BoldText>시작하기</BoldText>
          </View>
      </TouchableHighlight>

        <TouchableHighlight
          underlayColor="#FFCC00"
          onPress={toggleGPS}>
          <View style={styles.bottomSection}>
            <BoldText>{collectingGPS ? 'GPS 수집중' : 'GPS 수집'}</BoldText>
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
  bottomSection: {
    backgroundColor: '#FFFFFF', // 노란색 배경
    paddingVertical: 120,
    paddingHorizontal: 40,
    alignItems: 'center', // 내용 중앙 정렬
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 3,
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
export default Start;