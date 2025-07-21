import { StyleSheet} from 'react-native';

const fonts = StyleSheet.create({
    normal: { fontSize: 15,alignSelf: "center", color: "#000000" },
    bold: { fontSize: 32, color: "#000000",fontWeight: 'bold' },
    button: { fontSize: 40, alignSelf: "center", color: "#000000"},
});

const scalingFactors = {normal: 20, big: 12};

module.exports = {fonts, scalingFactors}