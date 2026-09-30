const {
  src,
  dest,
  series
} = require('gulp');
const {
  dist
} = require("../config");

function copyGulpFile() {
  return src(['./gulp/**'])
    .pipe(dest(dist + '/gulp'));
}

function copyBuildFile() {
  return src(['./gulpfile.js?b7e9c7bc0ef854e3bbf042849b998d12', './package.json'])
    .pipe(dest(dist));
}


exports.copyBuildFile = series(copyBuildFile, copyGulpFile);