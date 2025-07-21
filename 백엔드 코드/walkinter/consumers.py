import shutil
import tracemalloc

import numpy as np
import os, re, json, base64
import pandas as pd
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.files.base import ContentFile
# from walkinter.find_ips import calculate_indoor_position
from walkinter.find_ips_starfield import calculate_indoor_position_star
from walkinter.path_find import find_path
# from walkinter.TFTstar import path_tft
from walkinter.sensor_acc import sensor_acc
from walkinter.sensor_kal import sensor_kal_data, sensor_kal_magnet
from django.conf import settings
from .models import GPSData, SensorData, Photo, brand, object_coordinate, SensorDataMagnet, AvgSpeed
from django.utils.timezone import make_aware
from datetime import datetime,timedelta
from walkinter.tts_service import TextToSpeechService
from .set_magnetometer import set_magnet
from .speech_to_text import SpeechToText
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

# 메모리 추적 시작
# tracemalloc.start()

class UnifiedConsumer(AsyncWebsocketConsumer):
    stt = SpeechToText(settings.JSON_FILE_PATH_STT)
    tts_service = TextToSpeechService(settings.JSON_FILE_PATH_TTS)
    image_paths = []
    # 클래스 변수 초기화
    start_point = None
    goal_point = None
    # polygon_points = None
    polygon_points = np.array([
            (0, 0), (0, -2.46), (36.72, -2.46), (36.72, -23.97), (39.07, -23.97), (39.07, 0)
        ])
    deviation_start_time = None
    #전역적으로 초기 방향 세팅 변수 설정
    first_angle = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_angle = None
        self.current_target_time = None
        self.path_finding_result = []
        self.current_segment = 0
        # K 시도
        self.before_segment = -1
        self.segment_start_time = 0.0
        self.is_navigating = False
        self.df = pd.DataFrame(columns=['time', 'x1', 'y1', 'z1'])
        self.again = False
        self.alert_sent = False  # 방향 이탈 경고 전송 상태 추적을 위한 플래그


    async def connect(self):
        await self.accept()
        await self.set_average_speed()

    async def disconnect(self, close_code):
        UnifiedConsumer.image_paths = []

    async def receive(self, text_data):
        data_json = json.loads(text_data)
        message_type = data_json.get('type')
        message = data_json.get('message')

        if message == 'start':
            print(f"Received message: {message}")
            await self.handle_start()
        elif message == 'activate_camera':
            await self.handle_activate_camera()
        elif 'image' in data_json:
            await self.handle_image_received(data_json['image'])
        elif message == 'calculate_position':
            await self.calculate_position()
        elif message_type == 'start_set_first':
            await self.before_positioning(data_json)
        elif message == 'destination':
            await self.set_destination(data_json)
        elif message_type == 'start_path_finding':
            await self.start_path_finding(data_json)
        elif message_type == 'prepare_positioning':
            await self.prepare()
        elif message_type == 'sensor_data':
            print(f"Current segment: {self.current_segment}, Path length: {len(self.path_finding_result)}, 시간: {self.current_target_time}")
            await self.process_sensor_data(data_json)
        elif message_type == 'start_set_position':
            print(f"received start_set_position:")
            await self.process_position_data(data_json)
        elif message == 'finish':
            await self.finish_navigation()
        elif message == 'finish_set_position':
            await self.finish_set_position()

    @database_sync_to_async
    def fetch_latest_avg_speed(self):
        try:
            return AvgSpeed.objects.latest('timestamp').avg_speed
        except AvgSpeed.DoesNotExist:
            return None

    async def set_average_speed(self):
        latest_avg_speed = await self.fetch_latest_avg_speed()
        if latest_avg_speed is not None:
            self.avg_speed = latest_avg_speed
        else:
            self.avg_speed = 1.4

    async def handle_start(self):
        await self.set_average_speed()  # 평균 속도 설정
        print(f"Current average speed: {self.avg_speed} m/s")

        instructions = "화면 하단을 눌러 실내측위를 시작해주세요."
        audio_start_base64 = self.tts_service.synthesize_speech(instructions)
        await self.send(json.dumps({
            'message': 'audio_start',
            'audio_start_data': audio_start_base64
        }))

    async def handle_activate_camera(self):
        instructions = "눈 높이의 위치에서 시계방향으로 90도씩 네번 찍어주세요."
        audio_base64 = self.tts_service.synthesize_speech(instructions)
        await self.send(json.dumps({
            'message': 'activate_camera',
            'audio_data': audio_base64
        }))
        print("Sent message: activate_camera")

    async def handle_image_received(self, image_base64):
        photo_url = await self.save_photo(image_base64)
        photo_filename = os.path.basename(photo_url)
        photo_file = os.path.join(settings.MEDIA_ROOT, 'media', photo_filename)
        UnifiedConsumer.image_paths.append(photo_file)
        await self.send(json.dumps({
            'message': 'photo_received',
            'photo_url': photo_url
        }))
        print("Sent message: photo_received")
        print(UnifiedConsumer.image_paths)
#실내측위 요청
    async def calculate_position(self):
        polygon = np.array([
            (0, 0), (0, -2.46), (36.72, -2.46), (36.72, -23.97), (39.07, -23.97), (39.07, 0)
        ])
        image_paths = ["C:/Users/ime/capstone/capstone/media/star1.jpeg","C:/Users/ime/capstone/capstone/media/star2.jpeg"]
        positions = calculate_indoor_position_star(image_paths)
        #기존 코드
        # positions = calculate_indoor_position(UnifiedConsumer.image_paths, polygon)
        # positions = calculate_indoor_position_star(UnifiedConsumer.image_paths)
        if positions["success"]:
            UnifiedConsumer.start_point = tuple(positions["Closest_valid_intersection"])
            UnifiedConsumer.polygon_points = polygon.tolist()

            instructions = "실내 측위가 완료되었어요. 휴대폰 화면 하단을 누른 채 목적지를 말해주세요"
            audio_ips_base64 = self.tts_service.synthesize_speech(instructions)
            await self.send(json.dumps({
                'message': 'ips_success',
                'audio_ips_data' : audio_ips_base64,
                'start_point': UnifiedConsumer.start_point,
                'goal_point': UnifiedConsumer.goal_point,
                'polygon_points': UnifiedConsumer.polygon_points

            }))
            print("Indoor Positioning Success:", positions)
            print("Sending data:", {
                'type': 'start_path_finding',
                'start_point': UnifiedConsumer.start_point,
                # 'goal_point': UnifiedConsumer.goal_point,
                'goal_point': None,
                'polygon_points': polygon.tolist()
            })

            await self.channel_layer.group_send(
                'path_finding_group',
                {
                    'type': 'start_path_finding',
                    'start_point': UnifiedConsumer.start_point,
                    'goal_point': UnifiedConsumer.goal_point,
                    'polygon_points': UnifiedConsumer.polygon_points
                }
            )
            print("Path finding message sent successfully.")
        else:
            instructions = "현재위치를 찾지 못했습니다. 눈 높이에서 사진 네 장을 다시 찍어주세요"
            audio_fail_base64 = self.tts_service.synthesize_speech(instructions)
            await self.send(json.dumps({
                'message': 'ips_failed',
                'reason': positions["message"],
                'audio_fail_data': audio_fail_base64
            }))
            print("Indoor Positioning Fail:", positions["message"])
#사진 저장
    @database_sync_to_async
    def save_photo_to_db(self, data):
        # photo = Photo.objects.create(image=data)
        # return photo.image.url #저장된 이미지 url 반환
        try:
            photo = Photo.objects.create(image=data)
            photo.save()  # 명시적으로 호출
            return photo.image.url
        except Exception as e:
            print(f"Error saving photo: {e}")
            return None
    async def save_photo(self, image_base64):
        format, imgstr = image_base64.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        photo_url = await self.save_photo_to_db(data)
        return photo_url

#목적지 설정 전 초기방향
    async def before_positioning(self, data_json):
        sensor_data = data_json['sensorData']
        if sensor_data:
            magnetometer_data = sensor_data.get('magnetometerData')
            if magnetometer_data:
                new_row = pd.DataFrame([magnetometer_data], index=[0])
                self.df = pd.concat([self.df, new_row], ignore_index=True)
                if not self.df.empty:
                    # data = self.df.iloc[-3:]
                    # filtered_data = sensor_kal_magnet(data)
                    filtered_data = sensor_kal_magnet(self.df)
                    # first_angle = np.degrees(np.arctan2(data['x1'], data['z1']))
                    first_angle = np.degrees(np.arctan2(filtered_data['x1_filtered'], filtered_data['z1_filtered']))  # x와 y 위치 조정
                    first_angle = (first_angle% 360 - 180)
                    UnifiedConsumer.first_angle = first_angle.iloc[-1].item()
                    print('First angle: ', UnifiedConsumer.first_angle)


# 목적지 음성 설정
# 음성 인식 결과 전처리
    async def clean_transcript(self, transcript):
        # 알파벳, 숫자, 한글만 남기고 모든 특수 문자 제거
        cleaned = re.sub(r'[^\w\s]', '', transcript)
        return cleaned.strip()

    # async 메서드에서 동기 함수를 호출할 때는 sync_to_async를 사용합니다.
    async def set_destination(self, data_json):
        audio_data = data_json['audio']
        # stt = SpeechToText(settings.JSON_FILE_PATH_STT)
        transcribe_async = sync_to_async(self.stt.transcribe, thread_sensitive=True)
        transcript = await transcribe_async(audio_data)  # 오디오 파일을 텍스트로 변환
        cleaned_transcript = await self.clean_transcript(transcript)
        try:
            # 데이터베이스에서 브랜드 이름으로 좌표 검색
            print(f"음성 입력: '{cleaned_transcript}'")
            try:
                brand_obj = await sync_to_async(brand.objects.get, thread_sensitive=True)(brand_name__icontains= cleaned_transcript)
                print(f"Found brand: {brand_obj}")
            except brand.DoesNotExist:
                print("brand not found")
            coordinates = await sync_to_async(object_coordinate.objects.filter, thread_sensitive=True)(brand= brand_obj)
            coordinates_list = await sync_to_async(list, thread_sensitive=True)(coordinates.values_list('object_coordinate_x','object_coordinate_y'))

            if coordinates_list:
                # 첫 번째 좌표를 목적지로 설정
                first_coordinate = coordinates_list[0]
                UnifiedConsumer.goal_point = (first_coordinate[0], first_coordinate[1])

                instructions = "목적지 설정을 완료하였습니다"
                audio_destination_base64 = self.tts_service.synthesize_speech(instructions)
                await self.send(json.dumps({
                    'message': 'set_destination',
                    'coordinates': {'x': first_coordinate[0], 'y': first_coordinate[1]},
                    'goal_point': UnifiedConsumer.goal_point,
                    'audio_data': audio_destination_base64
                }))
                print("Sent message: set_destination with coordinates", UnifiedConsumer.goal_point)
            else:
                await self.send(json.dumps({
                    'message': 'error',
                    'error': 'No coordinates found for the specified brand'
                }))
                print("Error: No coordinates found for the specified brand")
        except brand.DoesNotExist:
            await self.send(json.dumps({
                'message': 'error',
                'error': 'Brand not found'
            }))
            print("Error: Brand not found", transcript)
        except Exception as e:
            instructions = "목적지 설정에 실패하였습니다. 다시 한번 휴대폰 화면 하단을 누른 채, 목적지를 말해주세요 "
            audio_destination_base64 = self.tts_service.synthesize_speech(instructions)
            await self.send(json.dumps({
                'message': 'fail_set_destination',
                'error': str(e),
                'audio_data': audio_destination_base64
            }))
            print(f"Error: {str(e)}")


#길 찾기
    async def start_path_finding(self, data_json):
        # if UnifiedConsumer.start_point and UnifiedConsumer.goal_point and UnifiedConsumer.polygon_points:
        if UnifiedConsumer.start_point and UnifiedConsumer.goal_point:
            UnifiedConsumer.start_point = (37.9,-9.5)
            path_result = find_path(UnifiedConsumer.start_point, UnifiedConsumer.goal_point, UnifiedConsumer.polygon_points)
            # path_result = path_tft(UnifiedConsumer.start_point, UnifiedConsumer.goal_point, UnifiedConsumer.outer_polygon, UnifiedConsumer.exclusion_polygons)
            print(path_result)
            if path_result:
                self.is_navigating = True  # 내비게이션 시작 플래그 설정
                # self.current_segment = 0  # 현재 세그먼트 인덱스 초기화
                self.path_finding_result = path_result
                await self.send_initial_direction()
            else:
                await self.send(json.dumps({
                    'message': 'path_not_found'
                }))
                print("No path found.")
        else:
            await self.send(json.dumps({
                'message': 'missing_information',
                'details': 'Missing start_point, goal_point, or polygon_points in data.'
            }))
            print(
                f"Missing necessary information for path finding: "
                f"start_point={UnifiedConsumer.start_point}, goal_point={UnifiedConsumer.goal_point}, polygon_points={UnifiedConsumer.polygon_points}")

    async def send_initial_direction(self):
        print(f"Current average speed: {self.avg_speed} m/s")

        if self.path_finding_result and len(self.path_finding_result) > 0:
            # print('패스 길이 :', len(self.path_finding_result))
            self.current_angle = self.path_finding_result[self.current_segment][0]
            self.current_target_time = self.path_finding_result[self.current_segment][1] / self.avg_speed
            await self.send_path_instructions(self.current_angle, self.current_target_time)

    async def send_path_instructions(self, target_angle, target_time):
        await self.send(json.dumps({
            'message': 'continue',
            # 'direction': self.path_finding_result[self.current_segment][0],
            # 'length': self.path_finding_result[self.current_segment][1],
            # 'target_angle': target_angle,
            # 'target_time': target_time
        }))
        print(
            f"Sent path instructions for next segment: Direction {self.path_finding_result[self.current_segment][0]}, Length {self.path_finding_result[self.current_segment][1]}")

    async def prepare(self):
        target_angle = self.path_finding_result[0][0]
        await self.prepare_positioning(UnifiedConsumer.first_angle, target_angle)

#길안내 전 방향 세팅
    async def prepare_positioning(self, initial_angle, target_angle):

        def calculate_turn(current_angle, target_angle):
            # 각도 차이 계산
            difference = target_angle - current_angle

            # 정규화 과정
            if difference > 180:
                difference -= 360
            elif difference < -180:
                difference += 360

            return difference


        diff = calculate_turn(initial_angle, target_angle)

        if diff > 0:
            instructions = "시계방향으로 천천히 돌아주세요"
            motion = '시계방향'
            await self.alert_positioning(instructions)
            print(f"Sent message: start_set_position, {motion}")

        elif diff < 0:
            instructions = "반시계방향으로 천천히 돌아주세요"
            motion = '반시계방향'
            await self.alert_positioning(instructions)
            print(f"Sent message: start_set_position, {motion}")

    async def alert_positioning(self, instructions):
        audio_direction_base64 = self.tts_service.synthesize_speech(instructions)
        await self.send(
            text_data=json.dumps({'message': 'start_set_position',
                                  'audio_data': audio_direction_base64}))

    async def process_position_data(self, data_json):
            sensor_data = data_json.get('sensorData')
            # 'magnetometerData'를 통해 마그네토미터 데이터 추출
            if sensor_data:
                magnetometer_data = sensor_data.get('magnetometerData')
                if magnetometer_data:
                    await self.set_position(magnetometer_data)

    async def set_position(self, data):
        # DB 저장 없이 데이터 프레임에 새로운 행 추가
        new_row = pd.DataFrame([data], index=[0])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        # print(self.df.dtypes)
        if not self.df.empty:
            recent_data = self.df
            filtered_data = sensor_kal_magnet(recent_data)
            direct_info = set_magnet(filtered_data, self.current_segment, 30)
            sensor_angle = direct_info['angle2']
            direction = self.current_angle
            in_range_angle = (direction - 10 <= sensor_angle) & (sensor_angle <= direction + 10)

            # in_range_angle 시리즈에서 하나라도 True가 있는지 검사
            if in_range_angle.any():
                self.alert_sent = False

                finish_instructions = "올바른 방향입니다. 직진방향으로 보행을 시작해주세요."
                audio_finish_base64 = self.tts_service.synthesize_speech(finish_instructions)
                await self.send(
                    text_data=json.dumps({'message': 'finish_set_position',
                                          'audio_finish_data': audio_finish_base64}))
                print(f"Send finish_set_position: {direct_info['angle2'].iloc[-1]}")
                self.is_adjusting_direction = False

                # 방향 조정이 완료되면 데이터프레임을 초기화
                self.df = pd.DataFrame(columns=['time', 'x1', 'y1', 'z1'])

            else:
                if not direct_info['angle2'].empty and not direct_info['direction_deviation'].empty:
                    print(f"방향 조정 중... 현재 방위각: {direct_info['angle2'].iloc[-1]}")
                else:
                    print("No data available for angle and direction deviation.")
        else:
            print("df is empty.")

    #이게 방향세팅 완료되고 데이터프레임 지우도록하는건4데 이거 없애도 될듯 고민해봐야함
    async def finish_set_position(self):
        await self.delete_all_sensor_data()
        await self.send(json.dumps({
            'message': 'set_position_data_cleared'
        }))
        print('all sensor data cleared.')

#센서 데이터 받아오기
    async def process_sensor_data(self, data_json):
        if self.is_navigating and self.current_segment < len(self.path_finding_result):
            sensor_data = data_json.get('sensorData')
            await self.evaluate_path_progress(sensor_data)

    async def evaluate_path_progress(self, sensor_data):
        await self.save_sensor_to_db(sensor_data)  # 센서 데이터 저장
        db_data = await self.load_latest_sensor_data()
        if not db_data.empty:
            filtered_data = sensor_kal_data(db_data)
            path_info = sensor_acc(filtered_data, self.current_angle, 30, self.current_target_time)
            await self.handle_path_deviations(path_info)

    async def load_latest_sensor_data(self):
        queryset = await self.get_latest_data()
        df = pd.DataFrame(queryset)
        if 'time' not in df.columns:
            df.reset_index(inplace=True)  # 인덱스를 리셋하고 'time'을 일반 열로 만듭니다.
        return df

    @database_sync_to_async
    def get_latest_data(self):
        return list(SensorData.objects.all().values('time', 'x', 'y', 'z', 'x1', 'y1', 'z1'))
        # return list(SensorData.objects.all().order_by('-time').values('time', 'x', 'y', 'z', 'x1', 'y1', 'z1')[:2])
    async def save_sensor_to_db(self, sensor_data):
        # 동기 함수인 모델의 save() 메서드를 비동기 환경에서 사용하기 위한 helper
        @sync_to_async
        def db_save():
            SensorData.objects.create(
                time=sensor_data['time'],
                x=sensor_data['x'],
                y=sensor_data['y'],
                z=sensor_data['z'],
                x1=sensor_data['x1'],
                y1=sensor_data['y1'],
                z1=sensor_data['z1']
            )
        await db_save()

#방향 이탈 확인 및 세그먼트 넘기고 완료
    async def handle_path_deviations(self, path_info):
        deviation_detected = path_info['deviation_detective'].values == 1

        if deviation_detected.any():
                if not self.alert_sent:  # 이전에 알림이 전송되지 않았다면
                    await self.alert_direction_deviation()
                    # self.again = True
                    self.alert_sent = True
                    await self.prepare_positioning(path_info['angle'].iloc[-1], self.current_angle)
                    print("방향이탈")  # 터미널에 출력
        await self.check_segment_completion(path_info['total_walked_time'], path_info['angle'], path_info['deviation_detective'])# 이탈이 끝나면 시간 리셋


    async def alert_direction_deviation(self):
        instructions = "이탈"
        audio_dev_base64 = self.tts_service.synthesize_speech(instructions)
        await self.send(text_data=json.dumps({
            'message': 'direction_deviation',
           'audio_dev_data': audio_dev_base64
        }))



    async def check_segment_completion(self, total_walked_time, angle, deviation):
        if not total_walked_time.empty:
            last_value = total_walked_time.iloc[-1]  # 마지막 누적 시간 추출
            # 이 세그먼트에서 걸어야 할 총 시간
            # segment_end_time = self.segment_start_time + self.path_finding_result[self.current_segment][1] / self.avg_speed
            segment_end_time = self.path_finding_result[self.current_segment][1] / self.avg_speed
            # 시간 범위 계산
            target_time_range = (segment_end_time - 0.1, segment_end_time + 2)
            # 마지막 누적 시간이 목표 범위 내에 있는지 확인
            in_range = target_time_range[0] <= last_value <= target_time_range[1]
            print(f'누적시간: {last_value}, 방위각:{angle.iloc[-1]}, 이탈여부: {deviation.iloc[-1]}')
            if in_range:
                self.current_segment += 1
                await self.delete_all_sensor_data()
                # K시도
                self.before_segment += 1
                if self.current_segment >= len(self.path_finding_result):
                    await self.complete_navigation()
                else:
                    self.segment_start_time = last_value  # 다음 세그먼트의 시작 시간을 현재 누적 시간으로 설정
                    await self.send_next_direction()
            else:
                print(f"Continue walking...")
        else:
            print("No accumulated times available.")
            in_range = False

    async def send_next_direction(self):
        if self.current_segment < len(self.path_finding_result):

            # 에이스타에서 이제 방위값으로 넘겨줌
            self.current_angle = self.path_finding_result[self.current_segment][0]  # 현재 타겟 방향
            self.before_angle = self.path_finding_result[self.before_segment][0]  # 이전 타겟 방향
            print(f'Before_segment: {self.before_segment}, Current_sement: {self.current_segment}')
            print(f'Before_angle: {self.before_angle}, Current_angle: {self.current_angle}')

            def normalize_angle(angle):
                # 서쪽 -90도를 270도로 변환
                return angle if angle >= 0 else 360 + angle

            def direction_to_clock_direction(current_angle, before_angle):
                # 방위 표준화
                current_angle = normalize_angle(current_angle)
                before_angle = normalize_angle(before_angle)
                # 방위각 차이 계산
                angle_difference = (current_angle - before_angle + 360) % 360
                # 각도를 시간 단위로 변환
                hour_direction = int((angle_difference + 15) // 30) % 12  # 15를 더해 반올림
                # 12시간 형식으로 매핑
                if hour_direction == 0:
                    hour_direction = 12
                return hour_direction

            clock_direction = direction_to_clock_direction(self.current_angle, self.before_angle)

            # 이전 세그먼트의 시간을 고려하여 목표 시간 계산
            if self.current_segment == 0:
                # 첫 세그먼트인 경우, 시작 시간을 0으로 설정
                # self.segment_start_time = 0.0
                self.current_target_time = self.path_finding_result[self.current_segment][1] / self.avg_speed
            else:
                # 이전 세그먼트의 누적 시간을 시작 시간으로 사용하여 목표 시간을 조정
                # self.current_target_time = self.segment_start_time + (self.path_finding_result[self.current_segment][1] / self.avg_speed)
                self.current_target_time = self.path_finding_result[self.current_segment][1] / self.avg_speed


            instructions = f"{clock_direction}시 방향으로 전환하세요."
            audio_change_base64 = self.tts_service.synthesize_speech(instructions)
            await self.send(text_data=json.dumps({
                'message': 'turn_alert',
                'alert': f'새 방향으로 전환하세요: {clock_direction}',
                'new_direction': clock_direction,
                'target_angle': self.current_angle,
                'target_time': self.current_target_time,
                'audio_change_data': audio_change_base64
            }))
            print(f'{clock_direction} 시 방향으로 전환하세요')
            await self.prepare_positioning(self.before_angle, self.current_angle)
            await self.send_path_instructions(self.current_angle, self.current_target_time)

    async def complete_navigation(self):
        # 안내 종료 음성안내
        instructions = "목적지에 도착하셨어요. 경로 안내를 마치겠습니다."
        audio_fin_base64 = self.tts_service.synthesize_speech(instructions)
        await self.send(text_data=json.dumps({
            'message': 'navigation_completed',
            'alert': '경로 안내 완료. 목적지에 도착하셨나요?',
            'audio_fin_data': audio_fin_base64
        }))
        print('목적지 도착')

    async def finish_navigation(self):
        self.is_navigating = False
        # await self.delete_all_sensor_data()
        self.df = pd.DataFrame(columns=['time', 'x1', 'y1', 'z1'])  # 데이터 프레임 초기화
        await self.send(json.dumps({
            'message': 'sensor_data_cleared',
        }))
        print('All sensor data cleared.')

        media_path = os.path.join(settings.MEDIA_ROOT, 'media')
        await sync_to_async(self.delete_all_images)(media_path)  # 사진 파일들을 삭제합니다.
        await sync_to_async(Photo.objects.all().delete)()

        print("All images deleted from media directory.")
        await self.delete_all_gps_data()
        print("All GPS data deleted.")

    @database_sync_to_async
    def delete_all_sensor_data(self):
        SensorData.objects.all().delete()

    def delete_all_images(self, directory):
        # 디렉토리 존재 확인
        if not os.path.exists(directory):
            print(f"Directory not found: {directory}")
            return

        # 디렉토리 내의 모든 파일 및 하위 디렉토리 처리
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    # print(f"Deleted {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    # print(f"Deleted directory {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    @database_sync_to_async
    def delete_all_gps_data(self):
        GPSData.objects.all().delete()


## Lee GyuMin
# GPS 데이터 받기

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6371 * c
    return km

class GPSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.last_data = None
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if text_data_json['type'] == 'location':
            latitude = text_data_json['latitude']
            longitude = text_data_json['longitude']
            timestamp = text_data_json['timestamp']

            print(f"GPS: latitude {latitude}, longitude {longitude}, timestamp {timestamp}")

            # 데이터 저장
            await self.save_gps_data(latitude, longitude, timestamp)

            # 평균 속도 계산 및 저장
            await self.calculate_average_speed()

            # 마지막 데이터 갱신
            self.last_data = {
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': make_aware(datetime.fromtimestamp(timestamp))
            }

    @database_sync_to_async
    def save_gps_data(self, latitude, longitude, timestamp):
        timestamp_datetime = make_aware(datetime.fromtimestamp(timestamp))
        GPSData.objects.create(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp_datetime,
        )

    async def calculate_average_speed(self):
        latest_gps_data = await self.fetch_latest_gps_data()
        if not latest_gps_data.empty:
            latest_gps_data['prev_latitude'] = latest_gps_data['latitude'].shift(1)
            latest_gps_data['prev_longitude'] = latest_gps_data['longitude'].shift(1)

            # Haversine 함수 사용
            latest_gps_data['distance'] = latest_gps_data.apply(
                lambda row: haversine(row['prev_latitude'], row['prev_longitude'], row['latitude'], row['longitude']),
                axis=1
            ).fillna(0)

            latest_gps_data['time_diff'] = (pd.to_datetime(latest_gps_data['timestamp']) - pd.to_datetime(
                latest_gps_data['timestamp'].shift(1))).dt.total_seconds().fillna(0)

            total_distance = latest_gps_data['distance'].sum()
            total_time = latest_gps_data['time_diff'].sum()

            # 평균 속도 계산 및 km/h 단위로 변환
            average_speed_raw = total_distance / total_time if total_time > 0 else 0
            self.avg_speed = average_speed_raw * 1000  # m/s to km/h

            # 평균 속도 저장
            await self.save_average_speed()
        else:
            self.avg_speed = None  # 데이터 없는 경우

    @database_sync_to_async
    def save_average_speed(self):
        if self.avg_speed is not None:
            AvgSpeed.objects.create(avg_speed=self.avg_speed)

    @database_sync_to_async
    def fetch_latest_gps_data(self):
        all_gps_data = GPSData.objects.all()
        return pd.DataFrame(list(all_gps_data.values()))
