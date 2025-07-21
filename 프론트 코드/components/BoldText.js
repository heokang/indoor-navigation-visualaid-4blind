import React, { Component } from 'react';
import { StyleSheet, Text, View, Dimensions } from 'react-native';
import { fonts, scalingFactors } from '../styles/fonts';

let { width } = Dimensions.get("window");

class BoldText extends Component {
    static displayName = "BoldText";

    render() {
        return (
            <Text style = {[this.props.stlye, fonts.bold, scaled.big ]}>
                {this.props.children}
            </Text>
        );
    }
}

const scaled = StyleSheet.create({
    big: { fontSize: width*1.5 / scalingFactors.big }
});

export default BoldText;