--[[
		Thank you for using UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw.

		If you didn't save in Binary (rbxl) - it's recommended to save the game right away to take advantage of the binary format & to preserve values of certain properties if you used IgnoreDefaultProperties setting (as they might change in the future).
		You can do that by going to FILE -> Save to File As -> Make sure File Name ends with .rbxl -> Save

		ServerStorage, ServerScriptService and Server Scripts are IMPOSSIBLE to save because of FilteringEnabled.

		If your player cannot spawn into the game, please move the scripts in StarterPlayer somewhere else or delete them. Then run `game:GetService("Players").CharacterAutoLoads = true`.
		And use "Play Here" to start game instead of "Play" to spawn your Character where your Camera currently is.

		If the chat system does not work, please use the explorer and delete everything inside the TextChatService/Chat service(s). 
		Or run `game:GetService("Chat"):ClearAllChildren() game:GetService("TextChatService"):ClearAllChildren()`
				
		If Union and MeshPart collisions don't work, run the script below in the Studio Command Bar:
				
				
		local C = game:GetService("CoreGui")
		local D = Enum.CollisionFidelity.Default
				
		for _, v in game:GetDescendants() do
			if v:IsA("TriangleMeshPart") and not v:IsDescendantOf(C) then
				v.CollisionFidelity = D
			end
		end
		print("Done")
				
		If you can't move the Camera, run this script in the Studio Command Bar:
			
		workspace.CurrentCamera.CameraType = Enum.CameraType.Fixed
		
		Or Destroy the Camera.

		This file was generated with the following settings:
		{"SaveBytecode":false,"Callback":false,"ShowStatus":true,"IgnoreDefaultPlayerScripts":true,"NilInstancesFixes":{"BaseWrap":null,"Animator":null,"Attachment":null,"PackageLink":null,"AdPortal":null},"IgnoreList":["CoreGui","CorePackages"],"__DEBUG_MODE":false,"DecompileJobless":false,"IgnoreNotArchivable":true,"RemovePlayerCharacters":true,"Object":false,"DecompileIgnore":["TextChatService"],"IgnoreSpecialProperties":false,"TreatUnionsAsParts":false,"IsModel":false,"NilInstances":false,"ExtraInstances":[],"noscripts":false,"ReadMe":true,"scriptcache":true,"OptionsAliases":{"IgnoreArchivable":"IgnoreNotArchivable","DecompileTimeout":"timeout","SaveNonCreatable":"SaveNotCreatable","SavePlayers":"IsolatePlayers","FileName":"FilePath","IgnoreDefaultProps":"IgnoreDefaultProperties"},"AlternativeWritefile":true,"mode":"optimized","SaveCacheInterval":56320,"SharedStringOverwrite":false,"IsolatePlayers":false,"IgnoreSharedStrings":true,"timeout":10,"NotCreatableFixes":["","AdvancedDragger","AnimationTrack","Dragger","Player","PlayerGui","PlayerMouse","PlayerMouse","PlayerScripts","ScreenshotHud","StudioData","TextChatMessage","TextSource","TouchTransmitter","Translator"],"Anonymous":false,"IgnoreDefaultProperties":true,"IsolateStarterPlayer":false,"IgnorePropertiesOfNotScriptsOnScriptsMode":false,"IsolateLocalPlayerCharacter":false,"SaveNotCreatable":false,"IsolateLocalPlayer":false,"FilePath":false,"AntiIdle":true,"ShutdownWhenDone":false,"SafeMode":false,"IgnoreProperties":[]}

		Elapsed time: 134.73760590000165 PlaceId: 706824758 PlaceVersion: 4733 Client Version: 0.698.0.6980936 Executor: SirHurt 5.4.1
]]