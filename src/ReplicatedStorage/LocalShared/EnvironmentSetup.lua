-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:59 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.SPImageLoader)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.SPSoundLoader)
local v_u_10 = require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SaleInfo)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_14 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_15 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_16 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_17 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_18 = require(game.ReplicatedStorage.LocalShared.LocalEnvironmentDecorationSetup)
local v_u_19 = require(game.ReplicatedStorage.Shared.AssertType)
if v_u_5:is_dev_build() and not game:GetService("RunService"):IsClient() then
    v_u_2:errf("EnvironmentSetup included in server")
end;
local v_u_20 = {
    ["Mode"] = {
        ["None"] = 0,
        ["Lobby"] = 1,
        ["Game"] = 2,
        ["LobbyWithGameArena"] = 3,
        ["LobbyHalloween"] = 4
    },
    ["should_hide_npcs"] = function(_, _) --[[ Name: should_hide_npcs ]] --[[ Line: 272 ]]
        return false;
    end,
    ["get_default_collisiongroup_id"] = function(_) --[[ Name: get_default_collisiongroup_id ]] --[[ Line: 744 ]]
        return 0;
    end,
    ["get_transparent_collisiongroup_id"] = function(_) --[[ Name: get_transparent_collisiongroup_id ]] --[[ Line: 745 ]]
        return 1;
    end,
    ["get_invisiblewall_collisiongroup_id"] = function(_) --[[ Name: get_invisiblewall_collisiongroup_id ]] --[[ Line: 746 ]]
        return 2;
    end,
    ["get_uielements_collisiongroup_id"] = function(_) --[[ Name: get_uielements_collisiongroup_id ]] --[[ Line: 747 ]]
        return 3;
    end,
    ["get_no_trigger_dance_sync_attribute_name"] = function(_) --[[ Name: get_no_trigger_dance_sync_attribute_name ]] --[[ Line: 748 ]]
        return "NoTriggerDanceSync";
    end
}
local v_u_21 = nil
v_u_20.set_local_services = function(_, p22) --[[ Name: set_local_services ]] --[[ Line: 42 ]]
    --[[ Upvalues: (ref 1): v_u_21 ]]
    v_u_21 = p22
end;
local v_u_23 = nil
local v_u_24 = nil
v3:new()
local v_u_25 = CFrame.new()
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
local v_u_31 = nil
local v_u_32 = nil
local v_u_33 = nil
local v_u_34 = nil
local v_u_35 = nil
local v_u_36 = nil
local v_u_37 = nil
local v_u_38 = nil
local v_u_39 = nil
local v_u_40 = nil
local v_u_41 = nil
local v_u_42 = nil
local v_u_43 = nil
local v_u_44 = nil
local v_u_45 = nil
v_u_20.get_camera = function(_) --[[ Name: get_camera ]] --[[ Line: 75 ]]
    --[[ Upvalues: (ref 1): v_u_45 ]]
    return v_u_45;
end;
v_u_20.get_local_elements_folder = function(_) --[[ Name: get_local_elements_folder ]] --[[ Line: 80 ]]
    --[[ Upvalues: (ref 1): v_u_30 ]]
    return v_u_30;
end;
v_u_20.get_world_ui_folder = function(_) --[[ Name: get_world_ui_folder ]] --[[ Line: 81 ]]
    --[[ Upvalues: (ref 1): v_u_33 ]]
    return v_u_33;
end;
v_u_20.get_game_environment_center_cframe = function(_) --[[ Name: get_game_environment_center_cframe ]] --[[ Line: 82 ]]
    --[[ Upvalues: (ref 1): v_u_25 ]]
    return v_u_25;
end;
v_u_20.get_adornpool_root = function(_) --[[ Name: get_adornpool_root ]] --[[ Line: 83 ]]
    --[[ Upvalues: (ref 1): v_u_35 ]]
    return v_u_35;
end;
v_u_20.get_lobby_ui_proto_root = function(_) --[[ Name: get_lobby_ui_proto_root ]] --[[ Line: 84 ]]
    --[[ Upvalues: (ref 1): v_u_37 ]]
    return v_u_37;
end;
v_u_20.get_editor_game_proto_root = function(_) --[[ Name: get_editor_game_proto_root ]] --[[ Line: 85 ]]
    --[[ Upvalues: (ref 1): v_u_38 ]]
    return v_u_38;
end;
v_u_20.get_game_lighting = function(_) --[[ Name: get_game_lighting ]] --[[ Line: 86 ]]
    --[[ Upvalues: (ref 1): v_u_39 ]]
    return v_u_39;
end;
v_u_20.get_game_sky = function(_) --[[ Name: get_game_sky ]] --[[ Line: 87 ]]
    --[[ Upvalues: (ref 1): v_u_40 ]]
    return v_u_40;
end;
v_u_20.get_game_atmosphere = function(_) --[[ Name: get_game_atmosphere ]] --[[ Line: 88 ]]
    --[[ Upvalues: (ref 1): v_u_41 ]]
    return v_u_41;
end;
v_u_20.get_game_depth_of_field = function(_) --[[ Name: get_game_depth_of_field ]] --[[ Line: 89 ]]
    --[[ Upvalues: (ref 1): v_u_42 ]]
    return v_u_42;
end;
v_u_20.get_game_color_correction = function(_) --[[ Name: get_game_color_correction ]] --[[ Line: 90 ]]
    --[[ Upvalues: (ref 1): v_u_43 ]]
    return v_u_43;
end;
v_u_20.get_move_to_environment = function(_) --[[ Name: get_move_to_environment ]] --[[ Line: 91 ]]
    --[[ Upvalues: (ref 1): v_u_44 ]]
    return v_u_44;
end;
local l_Sky_0 = Instance.new("Sky")
v_u_20.initial_setup = function(_) --[[ Name: initial_setup ]] --[[ Line: 95 ]]
    --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_39, (ref 3): v_u_40, (copy 4): v_u_5, (ref 5): l_Sky_0, (ref 6): v_u_41, (ref 7): v_u_42, (ref 8): v_u_43, (ref 9): v_u_34, (ref 10): v_u_25, (ref 11): v_u_26, (ref 12): v_u_44, (ref 13): v_u_27, (ref 14): v_u_31, (ref 15): v_u_32, (ref 16): v_u_37, (ref 17): v_u_38, (copy 18): v_u_4, (copy 19): v_u_13, (ref 20): v_u_30, (ref 21): v_u_33, (ref 22): v_u_29, (ref 23): v_u_28, (ref 24): v_u_23, (copy 25): v_u_8, (ref 26): v_u_24, (copy 27): v_u_9, (ref 28): v_u_35, (ref 29): v_u_36, (copy 30): v_u_14, (copy 31): v_u_15 ]]
    v_u_45 = workspace.CurrentCamera
    v_u_45.CameraType = Enum.CameraType.Scriptable
    v_u_39 = game.Lighting
    v_u_40 = v_u_5:first_child_of_type(game.Lighting, "Sky")
    l_Sky_0 = v_u_40:Clone()
    v_u_41 = Instance.new("Atmosphere", v_u_39)
    v_u_42 = Instance.new("DepthOfFieldEffect", v_u_39)
    v_u_42.Enabled = false
    v_u_43 = Instance.new("ColorCorrectionEffect", v_u_39)
    v_u_43.Enabled = false
    v_u_34 = game.ReplicatedStorage.CharacterProtos.Default
    local v46 = game.Workspace:FindFirstChild("GameEnvironment")
    if v46 == nil then
        v46 = game.ReplicatedStorage.GameEnvironment
    end;
    v_u_25 = v46.PrimaryPart.CFrame
    v_u_26 = game.Workspace:FindFirstChild("Environment")
    if v_u_26 == nil then
        v_u_26 = game.ReplicatedStorage.Environment
    end;
    v_u_44 = game.Workspace:FindFirstChild("MoveToEnvironment")
    if v_u_44 then
        v_u_44.Parent = v_u_26
    end;
    v_u_27 = Instance.new("Model")
    v_u_27.Name = "LobbyEnvironmentNoPopper"
    v_u_27.Parent = game.Workspace
    v_u_31 = game.Workspace.LobbyCharacters
    v_u_32 = Instance.new("Folder", game.Workspace)
    v_u_32.Name = v_u_5:gen_name("LocalCharacter")
    if game.Workspace:FindFirstChild("LobbyElementProtos") then
        game.Workspace.LobbyElementProtos.Parent = game.ReplicatedStorage
    end;
    v_u_37 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto
    if game.Workspace:FindFirstChild("EditorGameElementProtos") then
        game.Workspace.EditorGameElementProtos.Parent = game.ReplicatedStorage
    end;
    v_u_38 = game.ReplicatedStorage.EditorGameElementProtos
    local v47 = v_u_4:new():push_back_table_list({ v_u_13:singleton():get_preload_assetid_table(), v46.ElementProtos, v46.WorldUIProto })
    v46.ElementProtos.Parent = game.ReplicatedStorage
    v46.WorldUIProto.Parent = game.ReplicatedStorage
    v_u_30 = Instance.new("Folder", game.Workspace)
    v_u_30.Name = "LocalElements"
    v_u_30.Name = v_u_5:gen_name(v_u_30.Name)
    v_u_33 = Instance.new("Folder", game.Workspace)
    v_u_33.Name = v_u_5:gen_name("WorldUI")
    v_u_29 = Instance.new("Folder", game.Workspace)
    v_u_29.Name = "LocalNPCs"
    v_u_28 = game.Workspace.LobbyAnchors
    v46.Parent = nil
    v_u_26.Parent = nil
    v_u_27.Parent = nil
    v_u_23 = v_u_8:new(v_u_4:new():push_back_table_list({ v_u_26 }), v47)
    v_u_24 = v_u_9:new()
    local l_Folder_0 = Instance.new("Folder", game.Workspace)
    l_Folder_0.Name = v_u_5:gen_name("AdornPoolParent")
    v_u_35 = Instance.new("Part", l_Folder_0)
    v_u_35.Name = v_u_5:gen_name("AdornPoolRoot")
    v_u_35.CFrame = CFrame.new()
    v_u_35.Size = Vector3.new()
    v_u_35.Transparency = 1
    v_u_35.Anchored = true
    v_u_35.CanCollide = false
    v_u_36 = game.Workspace.IntersectZones
    v_u_36.Parent = nil
    v_u_14:do_environment_setup()
    v_u_15:setup_game_stages()
end;
v_u_20.setup_on_initial_load_lobby = function(_) --[[ Name: setup_on_initial_load_lobby ]] --[[ Line: 201 ]]
    --[[ Upvalues: (copy 1): v_u_19, (ref 2): v_u_21, (copy 3): v_u_18 ]]
    v_u_19:is_non_nil(v_u_21)
    v_u_18:setup_environment_decorations(v_u_21)
end;
v_u_20.load_db_npc_character_and_humanoid = function(_, p_u_48, p_u_49, p_u_50) --[[ Name: load_db_npc_character_and_humanoid ]] --[[ Line: 206 ]]
    --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_2, (copy 3): v_u_16, (copy 4): v_u_12, (copy 5): v_u_5, (ref 6): v_u_29 ]]
    local v51 = v_u_17:get_category_name_to_id(v_u_17.Category.NPC):get(p_u_48)
    if v51 == nil then
        v_u_2:warnf("EnvironmentSetup:load_db_npc_character_and_humanoid(%s) modelid not found (nil)", (tostring(p_u_48)))
    end;
    v_u_16:singleton():load_model_category(v51, v_u_17.Category.NPC, function(p52) --[[ Line: 211 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_2, (copy 5): p_u_48, (ref 6): v_u_29, (copy 7): p_u_50 ]]
        if p_u_49 == true then
            Instance.new("BoolValue", p52).Name = v_u_12.NPC_PRIORITY_FLAG_NAME
        end;
        local v53 = v_u_5:first_child_of_type(p52, "Humanoid")
        if v53 == nil then
            v_u_2:warnf("EnvironmentSetup:load_db_npc_and_humanoid(%s) no humanoid", p_u_48)
            v53 = Instance.new("Humanoid", p52)
        end;
        p52.Parent = v_u_29
        p_u_50(p52, v53)
    end)
end;
v_u_20.get_npc_root = function(_) --[[ Name: get_npc_root ]] --[[ Line: 228 ]]
    --[[ Upvalues: (ref 1): v_u_29 ]]
    return v_u_29;
end;
v_u_20.get_lobby_environment = function(_) --[[ Name: get_lobby_environment ]] --[[ Line: 230 ]]
    --[[ Upvalues: (ref 1): v_u_26 ]]
    return v_u_26;
end;
v_u_20.get_lobby_environment_no_popper = function(_) --[[ Name: get_lobby_environment_no_popper ]] --[[ Line: 234 ]]
    --[[ Upvalues: (ref 1): v_u_27 ]]
    return v_u_27;
end;
v_u_20.get_lobby_anchors = function(_) --[[ Name: get_lobby_anchors ]] --[[ Line: 236 ]]
    --[[ Upvalues: (ref 1): v_u_28 ]]
    return v_u_28;
end;
v_u_20.get_intersect_zones_root = function(_) --[[ Name: get_intersect_zones_root ]] --[[ Line: 240 ]]
    --[[ Upvalues: (ref 1): v_u_36 ]]
    return v_u_36;
end;
v_u_20.set_lobby_characters_visible = function(_, p54) --[[ Name: set_lobby_characters_visible ]] --[[ Line: 242 ]]
    --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_21 ]]
    if p54 == true then
        v_u_31.Parent = game.Workspace
    else
        v_u_31.Parent = game.Lighting
    end;
    v_u_21._follow_npc_manager:set_npcs_visible(p54)
end;
v_u_20.set_local_character_visible = function(_, p55) --[[ Name: set_local_character_visible ]] --[[ Line: 251 ]]
    --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_21 ]]
    if p55 == true then
        v_u_32.Parent = game.Workspace
    else
        v_u_32.Parent = game.Lighting
    end;
    v_u_21._follow_npc_manager:set_local_npcs_visible(p55)
end;
v_u_20.move_to_local_character_folder = function(_, p56) --[[ Name: move_to_local_character_folder ]] --[[ Line: 260 ]]
    --[[ Upvalues: (ref 1): v_u_32 ]]
    p56.Parent = v_u_32
end;
v_u_20.get_lobby_characters_folder = function(_) --[[ Name: get_lobby_characters_folder ]] --[[ Line: 264 ]]
    --[[ Upvalues: (ref 1): v_u_31 ]]
    return v_u_31;
end;
v_u_20.get_local_character_folder = function(_) --[[ Name: get_local_character_folder ]] --[[ Line: 268 ]]
    --[[ Upvalues: (ref 1): v_u_32 ]]
    return v_u_32;
end;
local v_u_57 = true
v_u_20.set_show_other_players = function(_, p58) --[[ Name: set_show_other_players ]] --[[ Line: 278 ]]
    --[[ Upvalues: (ref 1): v_u_57, (copy 2): v_u_20 ]]
    if v_u_57 ~= p58 then
        v_u_20:set_lobby_characters_visible(p58)
    end;
    v_u_57 = p58
end;
v_u_20.get_show_other_players = function(_) --[[ Name: get_show_other_players ]] --[[ Line: 284 ]]
    --[[ Upvalues: (ref 1): v_u_57 ]]
    return v_u_57;
end;
local l_None_0 = v_u_20.Mode.None
local v_u_59 = v3:new():add_set_from_table_list({ v_u_20.Mode.Lobby, v_u_20.Mode.LobbyWithGameArena, v_u_20.Mode.LobbyHalloween })
v_u_20.is_mode_lobby = function(_) --[[ Name: is_mode_lobby ]] --[[ Line: 292 ]]
    --[[ Upvalues: (copy 1): v_u_59, (ref 2): l_None_0 ]]
    return v_u_59:contains(l_None_0);
end;
v_u_20.set_mode = function(_, p60) --[[ Name: set_mode ]] --[[ Line: 295 ]]
    --[[ Upvalues: (ref 1): v_u_39, (copy 2): v_u_1, (copy 3): v_u_5, (ref 4): v_u_40, (ref 5): l_Sky_0, (copy 6): v_u_20, (ref 7): l_None_0, (ref 8): v_u_26, (ref 9): v_u_27 ]]
    v_u_39.ClockTime = 12
    v_u_39.GeographicLatitude = 45
    v_u_39.OutdoorAmbient = v_u_1:new(150, 150, 150):to_color3()
    v_u_39.FogColor = v_u_1:new(191, 191, 191):to_color3()
    v_u_39.FogEnd = 100000
    v_u_39.FogStart = 0
    v_u_5:ptry(function() --[[ Line: 303 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): l_Sky_0 ]]
        v_u_40.SkyboxBk = l_Sky_0.SkyboxBk
        v_u_40.SkyboxDn = l_Sky_0.SkyboxDn
        v_u_40.SkyboxFt = l_Sky_0.SkyboxFt
        v_u_40.SkyboxLf = l_Sky_0.SkyboxLf
        v_u_40.SkyboxRt = l_Sky_0.SkyboxRt
        v_u_40.SkyboxUp = l_Sky_0.SkyboxUp
    end)
    v_u_40.SunTextureId = v_u_5:transparent_assetid()
    v_u_40.CelestialBodiesShown = false
    v_u_20:set_game_atmosphere_enabled(false)
    v_u_20:set_game_depth_of_field_enabled(false)
    v_u_20:set_game_color_correction_enabled(false)
    if p60 ~= l_None_0 then
        l_None_0 = p60
        if p60 == v_u_20.Mode.Lobby then
            v_u_39.Brightness = 1.25
            v_u_39.Ambient = v_u_1:new(0, 0, 0):to_color3()
            v_u_39.ColorShift_Bottom = v_u_1:new(120, 33, 195):to_color3()
            v_u_39.ColorShift_Top = v_u_1:new(38, 0, 165):to_color3()
            v_u_26.Parent = game.Workspace
            v_u_20:set_local_character_visible(true)
            v_u_20:set_lobby_characters_visible(true)
        elseif p60 == v_u_20.Mode.LobbyHalloween then
            v_u_39.Brightness = 0.25
            v_u_39.Ambient = v_u_1:new(56, 56, 56):to_color3()
            v_u_39.ColorShift_Bottom = v_u_1:new(120, 33, 195):to_color3()
            v_u_39.ColorShift_Top = v_u_1:new(38, 0, 165):to_color3()
            v_u_40.SunTextureId = "rbxassetid://7651071744"
            v_u_40.CelestialBodiesShown = true
            v_u_26.Parent = game.Workspace
            v_u_20:set_local_character_visible(true)
            v_u_20:set_lobby_characters_visible(true)
        elseif p60 == v_u_20.Mode.Game then
            v_u_39.Brightness = 0.25
            v_u_39.Ambient = v_u_1:new(150, 150, 150):to_color3()
            v_u_39.ColorShift_Bottom = v_u_1:new(0, 0, 0):to_color3()
            v_u_39.ColorShift_Top = v_u_1:new(0, 0, 0):to_color3()
            v_u_26.Parent = nil
            v_u_20:set_local_character_visible(false)
            v_u_20:set_lobby_characters_visible(false)
            v_u_20:set_compete_building_uis_visible(false)
        elseif p60 == v_u_20.Mode.LobbyWithGameArena then
            v_u_39.Brightness = 1
            v_u_39.ColorShift_Bottom = v_u_1:new(120, 33, 195):to_color3()
            v_u_39.ColorShift_Top = v_u_1:new(38, 0, 165):to_color3()
            v_u_26.Parent = game.Workspace
            v_u_20:set_local_character_visible(true)
            v_u_20:set_lobby_characters_visible(true)
        else
            v_u_26.Parent = nil
            v_u_20:set_local_character_visible(false)
            v_u_20:set_lobby_characters_visible(false)
        end;
        v_u_27.Parent = v_u_26.Parent
    end;
end;
local v_u_61 = v_u_4:new()
local v_u_62 = v_u_4:new()
local v_u_63 = false
local v_u_64 = v_u_4:new()
local v_u_65 = v_u_4:new()
v_u_20.get_gear_shop_available_equipmentids = function(_, p_u_66) --[[ Name: get_gear_shop_available_equipmentids ]] --[[ Line: 403 ]]
    --[[ Upvalues: (ref 1): v_u_63, (copy 2): v_u_64, (copy 3): v_u_65 ]]
    if v_u_63 then
        return p_u_66(v_u_64);
    end;
    v_u_65:push_back(function() --[[ Line: 407 ]]
        --[[ Upvalues: (copy 1): p_u_66, (ref 2): v_u_64 ]]
        p_u_66(v_u_64)
    end)
end;
v_u_20.post_connect_setup = function(_, p67) --[[ Name: post_connect_setup ]] --[[ Line: 413 ]]
    --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_26, (copy 3): v_u_61, (copy 4): v_u_4, (copy 5): v_u_11, (copy 6): v_u_6, (copy 7): v_u_20, (copy 8): v_u_62, (copy 9): v_u_64, (copy 10): v_u_10, (ref 11): v_u_34, (ref 12): v_u_63, (copy 13): v_u_65 ]]
    local v68 = v_u_5:get_list_of_children_of_classname(v_u_26.ShopBuilding.Building, "StringValue")
    for v69 = 1, v68:count() do
        local v70 = v68:get(v69)
        if v70.Value == "DecalDynamic" and (v70.Parent.ClassName == "Decal" or v70.Parent.ClassName == "MeshPart") then
            v_u_61:push_back(v70.Parent)
        end;
    end;
    p67._shop_local_protocol:request_shop_info_cached(function(p71) --[[ Line: 422 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_11, (ref 3): v_u_6, (ref 4): v_u_61 ]]
        local l_AvailableItems_0 = p71.AvailableItems
        local v72 = v_u_4:new()
        for v73 = 1, #l_AvailableItems_0 do
            local v74 = l_AvailableItems_0[v73]
            if v74.SaleComboKey == nil then
                v72:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v74.SongKey))
            else
                for _ = 1, 4 do
                    v72:push_back(v_u_11:get_shop_image_for_saleid(v74.SaleComboKey))
                end;
            end;
        end;
        if v72:count() > 0 then
            for v75 = 1, v_u_61:count() do
                local v76 = v_u_61:get(v75)
                local v77 = v72:random()
                if v76.ClassName == "Decal" then
                    v76.Texture = v77
                elseif v76.ClassName == "MeshPart" then
                    v76.TextureID = v77
                end;
            end;
        end;
    end)
    v_u_20:update_compete_building_uis(p67)
    local v78 = v_u_5:get_list_of_children_of_classname(v_u_26.ClothingShop.ClothingModels, "StringValue")
    for v79 = 1, v78:count() do
        local v80 = v78:get(v79)
        if v80.Value == "GearModel" and v80.Parent.ClassName == "Humanoid" then
            v_u_62:push_back(v80.Parent)
        end;
    end;
    p67._shop_local_protocol:request_gear_shop_info(function(p81) --[[ Line: 458 ]]
        --[[ Upvalues: (ref 1): v_u_64, (ref 2): v_u_62, (ref 3): v_u_10, (ref 4): v_u_34, (ref 5): v_u_63, (ref 6): v_u_65 ]]
        for v82 = 1, #p81.AvailableItems do
            v_u_64:push_back(p81.AvailableItems[v82].EquipmentID)
        end;
        if v_u_64:count() > 0 then
            for v83 = 1, v_u_62:count() do
                local v_u_84 = v_u_62:get(v83)
                v_u_10:character_modify_with_equipped_data(v_u_84.Parent, v_u_34, {
                    {
                        ["EquipmentID"] = v_u_64:random(),
                        ["Visible"] = true
                    }
                }, function() --[[ Line: 470 ]]
                    --[[ Upvalues: (copy 1): v_u_84 ]]
                    v_u_84.Parent.HumanoidRootPart.Anchored = true
                end)
            end;
        end;
        v_u_63 = true
        for _, v85 in v_u_65:key_itr() do
            v85()
        end;
        v_u_65:clear()
    end)
    v_u_20:update_dance_club_posters()
    v_u_20:update_marketplace_screens()
end;
v_u_20.get_gear_shop_model_humanoids = function(_) --[[ Name: get_gear_shop_model_humanoids ]] --[[ Line: 487 ]]
    --[[ Upvalues: (copy 1): v_u_62 ]]
    return v_u_62;
end;
local v_u_86 = v_u_4:new()
local v_u_87 = nil
v_u_20.set_compete_building_uis_visible = function(_, p88) --[[ Name: set_compete_building_uis_visible ]] --[[ Line: 491 ]]
    --[[ Upvalues: (ref 1): v_u_87, (copy 2): v_u_86 ]]
    if v_u_87 ~= p88 then
        v_u_87 = p88
        for v89 = 1, v_u_86:count() do
            v_u_86:get(v89).Enabled = p88
        end;
    end;
end;
v_u_20.update_compete_building_uis = function(_, p90) --[[ Name: update_compete_building_uis ]] --[[ Line: 499 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (copy 3): v_u_86, (ref 4): v_u_26, (copy 5): v_u_20, (copy 6): v_u_7, (copy 7): v_u_4 ]]
    local function f_update_placedisplay(p91, p_u_92) --[[ Name: update_placedisplay ]] --[[ Line: 500 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        if p91 == nil then
            p_u_92.Visible = false
        else
            v_u_5:get_user_thumbnail(p91.RbxID, function(p93) --[[ Line: 506 ]]
                --[[ Upvalues: (copy 1): p_u_92 ]]
                p_u_92.PlayerIconDisplay.Image = p93
            end, false)
            p_u_92.NameDisplay.Text = p91.PlayerName
            p_u_92.ScoreDisplay.Text = v_u_5:comma_value(p91.Score)
            p_u_92.GearMultiplierDisplay.Text = string.format("x%.2f", p91.GearMult)
        end;
    end;
    local function f_update_screen(p94, p95) --[[ Name: update_screen ]] --[[ Line: 514 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): f_update_placedisplay ]]
        if p94 == nil then
            p95.Visible = false
            return -1;
        end;
        p95.NameDisplay.Text = v_u_6:singleton():get_title_for_key(p94.SongKey)
        v_u_6:singleton():render_coverimage_for_key(p95.IconFrame.Icon, p95.IconFrame.IconOverlay, p94.SongKey)
        f_update_placedisplay(p94.LeaderboardPlaces[1], p95.Place1)
        f_update_placedisplay(p94.LeaderboardPlaces[2], p95.Place2)
        f_update_placedisplay(p94.LeaderboardPlaces[3], p95.Place3)
        f_update_placedisplay(p94.LeaderboardPlaces[4], p95.Place4)
        f_update_placedisplay(p94.LeaderboardPlaces[5], p95.Place5)
        f_update_placedisplay(p94.LeaderboardPlaces[6], p95.Place6)
        return p94.SongKey;
    end;
    local function _(p96, p97) --[[ Name: update_frontscreen_icon ]] --[[ Line: 533 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        if p97 <= 0 then
            p96.Visible = false
        else
            v_u_6:singleton():render_coverimage_for_key(p96.Icon, p96.IconOverlay, p97)
        end;
    end;
    v_u_86:push_back(v_u_26.CompeteBuilding.Screens.Screen1.SurfaceGui)
    v_u_86:push_back(v_u_26.CompeteBuilding.Screens.Screen2.SurfaceGui)
    v_u_86:push_back(v_u_26.CompeteBuilding.Screens.Screen3.SurfaceGui)
    v_u_86:push_back(v_u_26.CompeteBuilding.Screens.Screen4.SurfaceGui)
    v_u_26.CompeteBuilding.Screens.FrontScreen.SurfaceGui.Enabled = false
    v_u_20:set_compete_building_uis_visible(false)
    local function _() --[[ Name: hide_screens ]] --[[ Line: 548 ]]
        --[[ Upvalues: (ref 1): v_u_86 ]]
        for _, v98 in v_u_86:key_itr() do
            v98.Frame.Visible = false
        end;
    end;
    p90._evt:wait_on_event_once(v_u_7.EVT_Leaderboard_ServerResponseDisplayInfo, function(p99) --[[ Line: 554 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_86, (copy 3): f_update_screen, (ref 4): v_u_26, (ref 5): v_u_6 ]]
        local v100 = v_u_4:new(p99)
        if v100:count() <= 0 then
            for _, v101 in v_u_86:key_itr() do
                v101.Frame.Visible = false
            end;
        else
            local v102 = v_u_4:new()
            for _ = 1, 4 do
                if v100:count() == 0 then
                    for _, v103 in v_u_86:key_itr() do
                        v103.Frame.Visible = false
                    end;
                    return;
                end;
                local v104 = v100:random()
                v102:push_back(v104)
                v100:remove(v104)
            end;
            local v105 = f_update_screen(v102:get(1), v_u_26.CompeteBuilding.Screens.Screen1.SurfaceGui.Frame)
            local v106 = f_update_screen(v102:get(2), v_u_26.CompeteBuilding.Screens.Screen2.SurfaceGui.Frame)
            local v107 = f_update_screen(v102:get(3), v_u_26.CompeteBuilding.Screens.Screen3.SurfaceGui.Frame)
            local v108 = f_update_screen(v102:get(4), v_u_26.CompeteBuilding.Screens.Screen4.SurfaceGui.Frame)
            local l_Frame_0 = v_u_26.CompeteBuilding.Screens.FrontScreen.SurfaceGui.Frame
            local l_IconFrame1_0 = l_Frame_0.IconFrame1
            if v105 <= 0 then
                l_IconFrame1_0.Visible = false
            else
                v_u_6:singleton():render_coverimage_for_key(l_IconFrame1_0.Icon, l_IconFrame1_0.IconOverlay, v105)
            end;
            local l_IconFrame2_0 = l_Frame_0.IconFrame2
            if v106 <= 0 then
                l_IconFrame2_0.Visible = false
            else
                v_u_6:singleton():render_coverimage_for_key(l_IconFrame2_0.Icon, l_IconFrame2_0.IconOverlay, v106)
            end;
            local l_IconFrame3_0 = l_Frame_0.IconFrame3
            if v107 <= 0 then
                l_IconFrame3_0.Visible = false
            else
                v_u_6:singleton():render_coverimage_for_key(l_IconFrame3_0.Icon, l_IconFrame3_0.IconOverlay, v107)
            end;
            local l_IconFrame4_0 = l_Frame_0.IconFrame4
            if v108 <= 0 then
                l_IconFrame4_0.Visible = false
            else
                v_u_6:singleton():render_coverimage_for_key(l_IconFrame4_0.Icon, l_IconFrame4_0.IconOverlay, v108)
            end;
            v_u_26.CompeteBuilding.Screens.FrontScreen.SurfaceGui.Enabled = true
        end;
    end)
    p90._evt:fire_event_to_server(v_u_7.EVT_Leaderboard_ClientRequestDisplayInfo)
end;
v_u_20.get_default_character_clone = function(_) --[[ Name: get_default_character_clone ]] --[[ Line: 590 ]]
    --[[ Upvalues: (ref 1): v_u_34 ]]
    return v_u_34:Clone();
end;
v_u_20.get_character_model_for_playerid = function(_, p109) --[[ Name: get_character_model_for_playerid ]] --[[ Line: 592 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_34 ]]
    local v110 = game.ReplicatedStorage.CharacterProtos:FindFirstChild((tostring(p109)))
    if v110 == nil then
        v_u_2:warnf("EnvironmentSetup:get_character_model_for_playerid could not find playerid(%d)", p109)
        v110 = v_u_34:Clone()
    end;
    return v110;
end;
v_u_20.hide_scripts = function(_) --[[ Name: hide_scripts ]] --[[ Line: 601 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4 ]]
    for _, v111 in pairs(game.ReplicatedStorage.Lobby:GetChildren()) do
        if v111.ClassName ~= "LocalScript" then
            v111.Parent = nil
        end;
    end;
    local function f_recursive_deparent_and_rename(p112) --[[ Name: recursive_deparent_and_rename ]] --[[ Line: 609 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): f_recursive_deparent_and_rename ]]
        p112.Name = v_u_5:gen_name(p112.Name)
        for _, v113 in pairs(p112:GetChildren()) do
            f_recursive_deparent_and_rename(v113)
        end;
        p112.Parent = nil
    end;
    local v114 = v_u_4:new():push_back_table_list({
        game.ReplicatedStorage.AudioData,
        game.ReplicatedStorage.Avatar,
        game.ReplicatedStorage.Effects,
        game.ReplicatedStorage.Equipment,
        game.ReplicatedStorage.GameUI,
        game.ReplicatedStorage.Local,
        game.ReplicatedStorage.Menu,
        game.ReplicatedStorage.PlayerInfo,
        game.ReplicatedStorage.Server,
        game.ReplicatedStorage.Tutorial,
        game.ReplicatedStorage.Crafting,
        game.ReplicatedStorage.Shared,
        game.ReplicatedStorage.LocalShared,
        game.ReplicatedStorage.GameStage,
        game.ReplicatedStorage.Pets,
        game.ReplicatedStorage.SDK,
        game.ReplicatedStorage.SPChat,
        game.ReplicatedStorage.Tests,
        game.ReplicatedStorage.PreviewGame,
        game.ReplicatedStorage.LobbyDecoration
    })
    for v115 = 1, v114:count() do
        f_recursive_deparent_and_rename((v114:get(v115)))
    end;
end;
local v_u_116 = nil
v_u_20.hide_spremoteevent = function(_) --[[ Name: hide_spremoteevent ]] --[[ Line: 650 ]]
    --[[ Upvalues: (ref 1): v_u_116, (copy 2): v_u_5 ]]
    v_u_116 = game.ReplicatedStorage.Events
    v_u_116.SPRemoteEvent.Name = v_u_5:gen_name("SPRemoteEvent")
    v_u_116.SongDatabaseLoad.Name = v_u_5:gen_name("SongDatabaseLoad")
    v_u_116.Name = v_u_5:gen_name("Events")
end;
v_u_20.get_events_folder = function(_) --[[ Name: get_events_folder ]] --[[ Line: 657 ]]
    --[[ Upvalues: (ref 1): v_u_116 ]]
    return v_u_116;
end;
v_u_20.should_load_textures = function(_, p117) --[[ Name: should_load_textures ]] --[[ Line: 659 ]]
    --[[ Upvalues: (ref 1): v_u_23 ]]
    v_u_23:set_should_load(p117)
end;
v_u_20.get_image_loader = function(_) --[[ Name: get_image_loader ]] --[[ Line: 663 ]]
    --[[ Upvalues: (ref 1): v_u_23 ]]
    return v_u_23;
end;
v_u_20.update = function(_, p118, p119) --[[ Name: update ]] --[[ Line: 667 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
    v_u_23:update(p118, p119)
    v_u_24:update(p118, p119)
end;
v_u_20.update_dance_club_posters = function(_) --[[ Name: update_dance_club_posters ]] --[[ Line: 672 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (ref 3): v_u_26 ]]
    local v_u_120 = v_u_4:new():push_back_table_list({
        "rbxassetid://3194462455",
        "rbxassetid://3194462518",
        "rbxassetid://3194462570",
        "rbxassetid://3194462636",
        "rbxassetid://3194462697",
        "rbxassetid://3194462779",
        "rbxassetid://3194462848",
        "rbxassetid://3194462901",
        "rbxassetid://3194462951",
        "rbxassetid://3194462999",
        "rbxassetid://3194463052",
        "rbxassetid://3194463110"
    })
    v_u_5:try(function() --[[ Line: 688 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_26, (copy 3): v_u_120 ]]
        local v121 = v_u_5:get_list_of_children_of_classname(v_u_26.SubwayClub.PostersLeft, "Decal")
        for v122 = 1, v121:count() do
            v121:get(v122).Texture = v_u_120:random()
        end;
        local v123 = v_u_5:get_list_of_children_of_classname(v_u_26.SubwayClub.PostersRight, "Decal")
        for v124 = 1, v123:count() do
            v123:get(v124).Texture = v_u_120:random()
        end;
    end)
end;
v_u_20.update_marketplace_screens = function(_) --[[ Name: update_marketplace_screens ]] --[[ Line: 700 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (ref 3): v_u_26 ]]
    local v_u_125 = v_u_4:new({
        "rbxassetid://16203856765",
        "rbxassetid://16203856447",
        "rbxassetid://16203856201",
        "rbxassetid://16203855889",
        "rbxassetid://16203855700",
        "rbxassetid://16203855374"
    })
    local v_u_126 = 1
    v_u_5:try(function() --[[ Line: 710 ]]
        --[[ Upvalues: (copy 1): v_u_125, (ref 2): v_u_126, (ref 3): v_u_26 ]]
        local v_u_127 = 0
        local function f_r_itr(p128) --[[ Name: r_itr ]] --[[ Line: 712 ]]
            --[[ Upvalues: (copy 1): f_r_itr, (ref 2): v_u_125, (ref 3): v_u_126, (ref 4): v_u_127 ]]
            for _, v129 in pairs(p128:GetChildren()) do
                f_r_itr(v129)
            end;
            if (p128.ClassName == "Decal" or p128.ClassName == "Texture") and p128:GetAttribute("DecalTag") == "MarketplaceScreen" then
                p128.Texture = v_u_125:get(v_u_126)
                v_u_126 = v_u_126 + 1
                if v_u_126 > v_u_125:count() then
                    v_u_126 = 1
                end;
                v_u_127 = v_u_127 + 1
            end;
            if p128.ClassName == "MeshPart" and p128:GetAttribute("DecalTag") == "MarketplaceScreen" then
                p128.TextureID = v_u_125:get(v_u_126)
                v_u_126 = v_u_126 + 1
                if v_u_126 > v_u_125:count() then
                    v_u_126 = 1
                end;
                v_u_127 = v_u_127 + 1
            end;
        end;
        f_r_itr(v_u_26.Marketplace.InteriorNew.Screens)
    end)
end;
v_u_20.set_game_atmosphere_enabled = function(_, p130) --[[ Name: set_game_atmosphere_enabled ]] --[[ Line: 750 ]]
    --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_39 ]]
    if p130 then
        v_u_41.Parent = v_u_39
    else
        v_u_41.Parent = nil
    end;
end;
v_u_20.set_game_depth_of_field_enabled = function(_, p131) --[[ Name: set_game_depth_of_field_enabled ]] --[[ Line: 758 ]]
    --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_39 ]]
    if p131 then
        v_u_42.Enabled = true
        v_u_42.Parent = v_u_39
    else
        v_u_42.Parent = nil
    end;
end;
v_u_20.set_game_color_correction_enabled = function(_, p132) --[[ Name: set_game_color_correction_enabled ]] --[[ Line: 767 ]]
    --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_39 ]]
    if p132 then
        v_u_43.Enabled = true
        v_u_43.Parent = v_u_39
    else
        v_u_43.Parent = nil
    end;
end;
local s_MaterialService_0 = game:GetService("MaterialService")
local v_u_133 = v3:new()
v_u_20.load_custom_material = function(_, p134) --[[ Name: load_custom_material ]] --[[ Line: 778 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_133, (copy 3): s_MaterialService_0 ]]
    if p134.ClassName == "MaterialVariant" then
        if not v_u_133:contains(p134.Name) then
            local v135 = p134:Clone()
            v135.Parent = s_MaterialService_0
            v_u_133:add(v135.Name, v135)
        end;
    else
        return v_u_2:warnf("EnvironmentSetup:load_custom_material(%s) not a MaterialVariant", p134.Name);
    end;
end;
return v_u_20;
