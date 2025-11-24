-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_15 ]]
    v_u_12 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_13 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_14 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_15 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
local v16 = {}
local v_u_36 = {
    ["new"] = function(_, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_9, (copy 3): v_u_6 ]]
        local v19 = {}
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = 0
        local v_u_23 = Vector3.new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_3, (copy 3): p_u_17, (ref 4): v_u_21, (ref 5): v_u_9, (ref 6): v_u_23 ]]
            v_u_20 = v_u_3:get_list_of_children_of_classname(p_u_17, "MeshPart")
            v_u_20:remove_if(function(p24) --[[ Line: 41 ]]
                return p24.Material ~= Enum.Material.ForceField;
            end)
            v_u_21 = v_u_3:get_list_of_children_of_classname(p_u_17, "Decal")
            v_u_9:for_each(v_u_20, function(p25) --[[ Line: 46 ]]
                p25.Transparency = 1
            end)
            v_u_9:for_each(v_u_21, function(p26) --[[ Line: 49 ]]
                p26.Transparency = 1
            end)
            if v_u_20:count() > 0 then
                v_u_23 = v_u_20:get(1).Position
            end;
        end;
        v19.set_alpha = function(_, p27) --[[ Name: set_alpha ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_3, (ref 3): v_u_9, (ref 4): v_u_20, (ref 5): p_u_18, (ref 6): v_u_21 ]]
            v_u_22 = p27
            local v_u_28 = v_u_3:tra(v_u_22)
            v_u_9:for_each(v_u_20, function(p29) --[[ Line: 61 ]]
                --[[ Upvalues: (copy 1): v_u_28, (ref 2): p_u_18 ]]
                p29.Transparency = v_u_28
                p29.Color = p_u_18
            end)
            v_u_9:for_each(v_u_21, function(p30) --[[ Line: 65 ]]
                --[[ Upvalues: (copy 1): v_u_28, (ref 2): p_u_18 ]]
                p30.Transparency = v_u_28
                p30.Color3 = p_u_18
            end)
        end;
        v19.set_color = function(p31, p32) --[[ Name: set_color ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): p_u_18 ]]
            p_u_18 = p32
            return p31;
        end;
        v19.update = function(p33, p34) --[[ Name: update ]] --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_6 ]]
            if v_u_22 > 0 then
                v_u_22 = v_u_6:expt_sec(v_u_22, 0, 0.75, p34)
                p33:set_alpha(v_u_22)
            end;
        end;
        v19.has_any = function(_) --[[ Name: has_any ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21 ]]
            local v35
            if v_u_20:count() > 0 then
                v35 = v_u_21:count() > 0
            else
                v35 = false
            end;
            return v35;
        end;
        v19.can_animate = function(_) --[[ Name: can_animate ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_23 ]]
            return v_u_3:distance_to_camera(v_u_23) > 55;
        end;
        f_cons()
        return v19;
    end
}
v16.new = function(_) --[[ Name: new ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (copy 5): v_u_9, (copy 6): v_u_5, (ref 7): v_u_13, (ref 8): v_u_14, (copy 9): v_u_11, (copy 10): v_u_3, (copy 11): v_u_36, (copy 12): v_u_10, (copy 13): v_u_6, (copy 14): v_u_4 ]]
    local v37 = v_u_1:new()
    v_u_2:get_base_fn(v37, "get_name")
    v37.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 97 ]]
        return "Beyond Reality (Sound Space)";
    end;
    v_u_2:get_base_fn(v37, "get_icon")
    v37.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
        return "rbxassetid://11734386765";
    end;
    local v_u_38 = nil
    v37.load_stage = function(_, p_u_39) --[[ Name: load_stage ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_38 ]]
        v_u_7:singleton():load_model_category(v_u_8.GameStage.BeyondRealityCrystalStage, v_u_8.Category.GameStage, function(p40) --[[ Line: 103 ]]
            --[[ Upvalues: (ref 1): v_u_38, (copy 2): p_u_39 ]]
            v_u_38 = p40
            p_u_39()
        end)
    end;
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = v_u_9:new()
    local v_u_45 = v_u_9:new()
    local v_u_46 = 1
    local v_u_47 = 0
    local v_u_48 = v_u_9:new()
    local v_u_49 = v_u_9:new()
    local v_u_50 = nil
    local function f_update_color(p51) --[[ Name: update_color ]] --[[ Line: 120 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_50, (copy 3): v_u_49, (ref 4): v_u_45, (copy 5): v_u_48, (copy 6): v_u_44 ]]
        local v52 = v_u_5:get_server_game_instance_player_powerbar_active(p51._players._slots:get(p51:get_local_game_slot()))
        if v52 ~= v_u_50 then
            v_u_50 = v52
            local v53 = p51:get_game_note_skin_info()
            local v54 = v53:get_slot_basecolor_list(p51:get_local_game_slot())
            local v55 = v53:get_slot_fevercolor_list(p51:get_local_game_slot())
            local v56, v57, v58, v59
            if v52 then
                v56 = v55:get(1):to_color3()
                v57 = v55:get(2):to_color3()
                v58 = v55:get(3):to_color3()
                v59 = v55:get(4):to_color3()
            else
                v56 = v54:get(1):to_color3()
                v57 = v54:get(2):to_color3()
                v58 = v54:get(3):to_color3()
                v59 = v54:get(4):to_color3()
            end;
            v_u_49:clear()
            v_u_49:push_back(v56)
            v_u_49:push_back(v57)
            v_u_49:push_back(v58)
            v_u_49:push_back(v59)
            for _, v60 in v_u_45:key_itr() do
                v_u_48:push_back({ v60, (v_u_49:random()) })
            end;
            for _, v61 in v_u_44:key_itr() do
                v61:set_color(v_u_49:random())
            end;
        end;
    end;
    local function _() --[[ Name: pop_queued_color_change ]] --[[ Line: 156 ]]
        --[[ Upvalues: (copy 1): v_u_48 ]]
        if v_u_48:count() > 0 then
            local v62 = v_u_48:pop_back()
            v62[1].Color = ColorSequence.new(v62[2])
        end;
    end;
    v_u_2:get_base_fn(v37, "setup_stage")
    v37.setup_stage = function(p63, p64) --[[ Name: setup_stage ]] --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_38, (ref 3): v_u_13, (ref 4): v_u_42, (ref 5): v_u_14, (ref 6): v_u_11, (ref 7): v_u_45, (ref 8): v_u_3, (ref 9): v_u_50, (copy 10): v_u_48, (copy 11): f_update_color, (ref 12): v_u_9, (copy 13): v_u_44, (ref 14): v_u_36, (ref 15): v_u_43, (ref 16): v_u_10, (ref 17): v_u_46, (ref 18): v_u_6, (ref 19): v_u_47 ]]
        v_u_41 = v_u_38.CharacterShineProto
        v_u_41.Parent = nil
        v_u_38.Parent = v_u_13:get_local_elements_folder()
        v_u_42 = v_u_14:new(v_u_41, Vector3.new(0, -3.5, 0))
        local v65 = p64:get_game_note_skin_info():get_slot_basecolor_list(p64:get_local_game_slot())
        local v66 = v_u_11:get_default_base_color_list()
        local v67 = true
        for v68 = 1, v65:count() do
            if v65:get(v68):to_color3() ~= v66:get(v68):to_color3() then
                v67 = false
            end;
        end;
        local v69 = v67 and true or false
        v_u_45 = v_u_3:get_list_of_children_of_classname(v_u_38, "ParticleEmitter")
        v_u_45:shuffle()
        v_u_50 = nil
        v_u_48:clear()
        f_update_color(p64)
        local v70 = 0
        while v_u_48:count() > 0 do
            if v_u_48:count() > 0 then
                local v71 = v_u_48:pop_back()
                v71[1].Color = ColorSequence.new(v71[2])
            end;
            v70 = v70 + 1
            if v70 > 250 then
                break;
            end;
        end;
        local v72 = v_u_9:new()
        if v69 then
            v72:push_back(Color3.fromRGB(38, 115, 255))
            v72:push_back(Color3.fromRGB(137, 255, 38))
            v72:push_back(Color3.fromRGB(135, 38, 255))
            v72:push_back(Color3.fromRGB(255, 188, 38))
        else
            for _, v73 in v65:key_itr() do
                v72:push_back(v73:to_color3())
            end;
        end;
        v_u_44:clear()
        for _, v74 in pairs(v_u_38.BackCrystals:GetChildren()) do
            local v75 = v_u_36:new(v74, v72:random())
            if v75:has_any() then
                v_u_44:push_back(v75)
            end;
        end;
        v_u_43 = v_u_38.FaceToPlayer
        p63:on_switch_focus_slot(p64)
        local v76 = v_u_13:get_game_sky()
        v76.SkyboxBk = "http://www.roblox.com/asset/?id=602429318"
        v76.SkyboxDn = "http://www.roblox.com/asset/?id=602428352"
        v76.SkyboxFt = "http://www.roblox.com/asset/?id=602429732"
        v76.SkyboxLf = "http://www.roblox.com/asset/?id=602427899"
        v76.SkyboxRt = "http://www.roblox.com/asset/?id=602428873"
        v76.SkyboxUp = "http://www.roblox.com/asset/?id=602430059"
        local v77 = v_u_13:get_game_lighting()
        v77.Ambient = Color3.fromRGB(75, 75, 75)
        v77.Brightness = 1
        v77.ColorShift_Bottom = Color3.new(0.882353, 0.254902, 0.92549)
        v77.ColorShift_Top = Color3.new(0.466667, 0.105882, 0.647059)
        v77.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
        v77.ClockTime = 12
        v77.GeographicLatitude = 45
        v_u_46 = v_u_6:YForPointOf2PtLineP1P2X(5, 6, 30, 1, v_u_3:clamp(v_u_10:singleton():get_difficulty_for_key(p64:es_gamelocal_get_audiomanager():get_song_key()), 5, 30))
        v_u_47 = 0
    end;
    v_u_2:get_base_fn(v37, "on_switch_focus_slot")
    v37.on_switch_focus_slot = function(_, p78) --[[ Name: on_switch_focus_slot ]] --[[ Line: 257 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_4 ]]
        v_u_43:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p78:get_local_game_slot())))
    end;
    v_u_2:get_base_fn(v37, "create_shine_for_slot_at_cframe")
    v37.create_shine_for_slot_at_cframe = function(_, p79, p80, p81) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 265 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        v_u_42:create_shine_for_slot_at_cframe(p79, p80, p81)
    end;
    v_u_2:get_base_fn(v37, "process_character_location_for_slot")
    v37.process_character_location_for_slot = function(_, p82, p83, p84, p85) --[[ Name: process_character_location_for_slot ]] --[[ Line: 270 ]]
        return p82, p83, p84, p85;
    end;
    v_u_2:get_base_fn(v37, "game_update")
    v37.game_update = function(_, p86, p87) --[[ Name: game_update ]] --[[ Line: 275 ]]
        --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_47, (ref 3): v_u_46, (copy 4): v_u_44, (copy 5): f_update_color, (copy 6): v_u_48 ]]
        v_u_42:update(p86, p87)
        if p87:es_gamelocal_get_audiomanager():is_beat() then
            v_u_47 = v_u_47 + 1
            if v_u_46 < v_u_47 then
                v_u_47 = 0
                for _ = 1, 10 do
                    local v88 = v_u_44:random()
                    if v88:can_animate() then
                        v88:set_alpha(1)
                        break;
                    end;
                end;
            end;
        end;
        for _, v89 in v_u_44:key_itr() do
            v89:update(p86)
        end;
        f_update_color(p87)
        if v_u_48:count() > 0 then
            local v90 = v_u_48:pop_back()
            v90[1].Color = ColorSequence.new(v90[2])
        end;
        if v_u_48:count() > 0 then
            local v91 = v_u_48:pop_back()
            v91[1].Color = ColorSequence.new(v91[2])
        end;
        if v_u_48:count() > 0 then
            local v92 = v_u_48:pop_back()
            v92[1].Color = ColorSequence.new(v92[2])
        end;
    end;
    v_u_2:get_base_fn(v37, "teardown_stage")
    v37.teardown_stage = function(_, p93) --[[ Name: teardown_stage ]] --[[ Line: 302 ]]
        --[[ Upvalues: (ref 1): v_u_42, (copy 2): v_u_44, (ref 3): v_u_45, (ref 4): v_u_41, (ref 5): v_u_43, (ref 6): v_u_38 ]]
        v_u_42:teardown(p93)
        v_u_44:clear()
        v_u_45:clear()
        v_u_41:Destroy()
        v_u_43:Destroy()
        v_u_38:Destroy()
    end;
    v_u_2:get_base_fn(v37, "should_do_game_start_zoom_in_effect")
    v37.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 312 ]]
        return true, 36.5, 16.8, 0.75;
    end;
    return v37;
end;
return v16;
