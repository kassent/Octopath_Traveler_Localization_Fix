import os
import shutil
import sys



TARGET_PATH = r'C:\Users\kassent\Desktop\UnrealPakSwitch'
OCTO_PATH = r'D:\SteamLauncher\steamapps\common\OCTOPATH TRAVELER\Octopath_Traveler\Content\Paks'

def main():
    scriptFolder = os.path.split(__file__)[0]
    sourceFolder = os.path.join(scriptFolder, 'Output')
    with os.scandir(sourceFolder) as it:
        for entry in it:
            if entry.is_file():
                fileName, filePath = entry.name, entry.path
                if fileName.startswith('TalkData_ZH_CH'):
                    outputFolder = os.path.join(TARGET_PATH, r'Octopath_Traveler\Content\Talk\Database')
                    if not os.path.exists(outputFolder):
                        os.makedirs(outputFolder)
                    shutil.copy2(filePath, outputFolder)
                elif fileName.startswith('GameTextZH_CN'):
                    outputFolder = os.path.join(TARGET_PATH, r'Octopath_Traveler\Content\GameText\Database')
                    if not os.path.exists(outputFolder):
                        os.makedirs(outputFolder)
                    shutil.copy2(filePath, outputFolder)
                elif fileName.endswith('.ttf'):
                    outputFolder = os.path.join(TARGET_PATH, r'Octopath_Traveler\Content\UI\Font')
                    if not os.path.exists(outputFolder):
                        os.makedirs(outputFolder)
                    shutil.copyfile(filePath, os.path.join(outputFolder, os.path.splitext(fileName)[0]) + '.ufont')
    os.chdir(os.path.join(TARGET_PATH, r'v4\2\3'))
    executeResult = os.popen(r'UnrealPak.exe ..\..\..\Octopath_Traveler-WindowsNoEditor_1_P.pak -Create=..\..\..\lista.txt -compress')
    for line in executeResult.read().splitlines():
        print(line)
    shutil.copy2(os.path.join(TARGET_PATH, 'Octopath_Traveler-WindowsNoEditor_1_P.pak'), OCTO_PATH)

if __name__ == '__main__':
    main()