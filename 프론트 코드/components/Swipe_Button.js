import React, { Component } from 'react';
import { StyleSheet, Text, Animated, View } from 'react-native';
import { PanGestureHandler, State } from 'react-native-gesture-handler';
import BoldText from "./BoldText";

class Swipe_Button extends Component {
  constructor(props) {
    super(props);
    this.translateY = new Animated.Value(0);
  }

  onGestureEvent = event => {
    this.translateY.setValue(event.nativeEvent.translationY);
  };

  onHandlerStateChange = event => {
    if (event.nativeEvent.oldState === State.ACTIVE) {
      Animated.spring(this.translateY, {
        toValue: 0,
        useNativeDriver: true,
      }).start();

      if (event.nativeEvent.translationY < -100) {
        if (this.props.onSwipeUp) {
          this.props.onSwipeUp();
        }
      }
      else if (event.nativeEvent.translationY > 100) {
      if (this.props.onSwipeDown) {
        this.props.onSwipeDown();
      }
    }
    }
  };

  render() {
    return (
      <PanGestureHandler
        onGestureEvent={this.onGestureEvent}
        onHandlerStateChange={this.onHandlerStateChange}>
        <Animated.View
          style={[
            styles.buttonStyle, // Updated style for button
            {
              transform: [{ translateY: this.translateY }],
            }
          ]}>
          <BoldText>
            {this.props.children}
          </BoldText>
        </Animated.View>
      </PanGestureHandler>
    );
  }
}

const styles = StyleSheet.create({
  textStyle: {
    fontWeight: 'bold',
    fontSize: 20,
    textAlign: 'center',
    color: '#000', // 텍스트 색상
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

export default Swipe_Button;