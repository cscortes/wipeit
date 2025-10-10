# Release Check List

**⚠️ WARNING: This tool is EXTREMELY DESTRUCTIVE and will PERMANENTLY DESTROY data! ⚠️**

**🚨 USE AT YOUR OWN RISK - ALL DATA WILL BE IRREVERSIBLY DESTROYED! 🚨**
- make sure modified/new files are conforming to the programming_style_guide
- make pre-git-prep
- make security
    - if fail stop, alert user to security issues!
    - else continue with next item on release check list.
- make tests
    - if fail stop, alert user that tests failed!
    - else continue with next item on release check list.
- bump symantic version
    - make sure version is changed in all python files including test files
- update all documentation, Changes, readme, testdesign, arch
- create a branch tag with this new version
- commit to git
