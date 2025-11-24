-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12 ]]
    v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_11 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_12 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
local v13 = {}
local v_u_26 = {
    ["new"] = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_8 ]]
        local v15 = {}
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local function _() --[[ Name: update_pos ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_17, (ref 3): v_u_18, (copy 4): p_u_14, (ref 5): v_u_16 ]]
            local v21 = v_u_20 + Vector3.new(0, math.sin(v_u_17) * v_u_18, 0)
            p_u_14:SetPrimaryPartCFrame(CFrame.new(v21, v21 + v_u_16 + Vector3.new(0, math.cos(v_u_17) * 0.25, 0)))
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_14, (ref 3): v_u_17, (ref 4): v_u_3, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_16 ]]
            v_u_20 = p_u_14.PrimaryPart.Position
            v_u_17 = v_u_3:rand_rangef(0, 6.283185307179586)
            v_u_18 = v_u_3:rand_rangef(3, 8)
            v_u_19 = v_u_3:rand_rangef(1, 2)
            local v22 = v_u_3:rand_rangef(0, 6.283185307179586)
            v_u_16 = Vector3.new(math.sin(v22), 0, (math.cos(v22)))
            local v23 = v_u_20 + Vector3.new(0, math.sin(v_u_17) * v_u_18, 0)
            p_u_14:SetPrimaryPartCFrame(CFrame.new(v23, v23 + v_u_16 + Vector3.new(0, math.cos(v_u_17) * 0.25, 0)))
        end;
        v15.update = function(_, p24) --[[ Name: update ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_8, (ref 3): v_u_19, (ref 4): v_u_20, (ref 5): v_u_18, (copy 6): p_u_14, (ref 7): v_u_16 ]]
            v_u_17 = v_u_8:IncrementWrap(v_u_17, v_u_8:SecondsToTick(v_u_19) * p24, 6.283185307179586)
            local v25 = v_u_20 + Vector3.new(0, math.sin(v_u_17) * v_u_18, 0)
            p_u_14:SetPrimaryPartCFrame(CFrame.new(v25, v25 + v_u_16 + Vector3.new(0, math.cos(v_u_17) * 0.25, 0)))
        end;
        v15.reset_to_default_position = function(_) --[[ Name: reset_to_default_position ]] --[[ Line: 63 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_20 ]]
            p_u_14:SetPrimaryPartCFrame(CFrame.new(v_u_20, Vector3.new(1, 0, 0)))
        end;
        v15.recalc_positions = function(_) --[[ Name: recalc_positions ]] --[[ Line: 70 ]]
            --[[ Upvalues: (copy 1): f_cons ]]
            f_cons()
        end;
        f_cons()
        return v15;
    end
}
v13.new = function(_) --[[ Name: new ]] --[[ Line: 78 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_7, (copy 5): v_u_9, (ref 6): v_u_10, (copy 7): v_u_5, (copy 8): v_u_26, (ref 9): v_u_11, (copy 10): v_u_4 ]]
    local v27 = v_u_1:new()
    v_u_2:get_base_fn(v27, "get_name")
    v27.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 82 ]]
        return "Castaways Concerts";
    end;
    v_u_2:get_base_fn(v27, "get_icon")
    v27.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 84 ]]
        return "rbxassetid://13717757940";
    end;
    local v_u_28 = nil
    v27.load_stage = function(_, p_u_29) --[[ Name: load_stage ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_28 ]]
        v_u_6:singleton():load_model_category(v_u_7.GameStage.BeachStage, v_u_7.Category.GameStage, function(p30) --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_28, (copy 2): p_u_29 ]]
            v_u_28 = p30
            p_u_29()
        end)
    end;
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = v_u_9:new()
    v_u_2:get_base_fn(v27, "setup_stage")
    v27.setup_stage = function(p38, p39) --[[ Name: setup_stage ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_10, (ref 3): v_u_5, (ref 4): v_u_31, (ref 5): v_u_34, (ref 6): v_u_35, (ref 7): v_u_36, (copy 8): v_u_37, (ref 9): v_u_26, (ref 10): v_u_32, (ref 11): v_u_33, (ref 12): v_u_11 ]]
        v_u_28.Parent = v_u_10:get_local_elements_folder()
        local v40 = v_u_10:get_game_sky()
        v40.SkyboxBk = "http://www.roblox.com/asset/?id=12262483248"
        v40.SkyboxDn = "http://www.roblox.com/asset/?id=12262483248"
        v40.SkyboxFt = "http://www.roblox.com/asset/?id=12262483248"
        v40.SkyboxLf = "http://www.roblox.com/asset/?id=12262483248"
        v40.SkyboxRt = "http://www.roblox.com/asset/?id=12262483248"
        v40.SkyboxUp = "http://www.roblox.com/asset/?id=12262483248"
        local v41 = v_u_10:get_game_lighting()
        v41.Ambient = v_u_5:new(40, 13, 0):to_color3()
        v41.Brightness = 0.4
        v41.ColorShift_Bottom = v_u_5:new(255, 255, 255):to_color3()
        v41.ColorShift_Top = v_u_5:new(255, 255, 255):to_color3()
        v41.OutdoorAmbient = v_u_5:new(70, 70, 70):to_color3()
        v41.ClockTime = 9.7
        v41.GeographicLatitude = 45
        local v42 = v_u_10:get_game_atmosphere()
        v42.Density = 0.4
        v42.Offset = 0
        v42.Glare = 0
        v42.Haze = 0
        v42.Color = v_u_5:new(0, 0, 0):to_color3()
        v42.Decay = v_u_5:new(0, 0, 0):to_color3()
        v_u_10:set_game_atmosphere_enabled(true)
        v_u_31 = v_u_28.FaceToPlayer
        p38:on_switch_focus_slot(p39)
        v_u_34 = v_u_31.BackgroundBoat.Boat
        v_u_35 = v_u_31.BackgroundBoat.Start
        v_u_36 = v_u_31.BackgroundBoat.End
        v_u_34.CFrame = v_u_35.CFrame
        for _, v43 in pairs(v_u_31.Seagulls:GetChildren()) do
            v_u_37:push_back(v_u_26:new(v43))
        end;
        v_u_32 = v_u_28.CharacterShineProto
        v_u_32.Parent = nil
        v_u_33 = v_u_11:new(v_u_32, Vector3.new(0, -3.5, 0))
    end;
    v_u_2:get_base_fn(v27, "on_switch_focus_slot")
    v27.on_switch_focus_slot = function(_, p44) --[[ Name: on_switch_focus_slot ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): v_u_37, (ref 2): v_u_31, (ref 3): v_u_4 ]]
        for _, v45 in v_u_37:key_itr() do
            v45:reset_to_default_position()
        end;
        v_u_31:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p44:get_local_game_slot())))
        for _, v46 in v_u_37:key_itr() do
            v46:recalc_positions()
        end;
    end;
    v_u_2:get_base_fn(v27, "teardown_stage")
    v27.teardown_stage = function(_, p47) --[[ Name: teardown_stage ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_34, (ref 4): v_u_35, (ref 5): v_u_36, (copy 6): v_u_37, (ref 7): v_u_33, (ref 8): v_u_28 ]]
        v_u_31 = nil
        v_u_32:Destroy()
        v_u_34 = nil
        v_u_35 = nil
        v_u_36 = nil
        v_u_37:clear()
        v_u_33:teardown(p47)
        v_u_28:Destroy()
    end;
    v_u_2:get_base_fn(v27, "create_shine_for_slot_at_cframe")
    v27.create_shine_for_slot_at_cframe = function(_, p48, p49, p50) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 184 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        v_u_33:create_shine_for_slot_at_cframe(p48, p49, p50)
    end;
    v_u_2:get_base_fn(v27, "game_update")
    v27.game_update = function(_, p51, p52) --[[ Name: game_update ]] --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_34, (ref 3): v_u_35, (ref 4): v_u_36, (copy 5): v_u_37 ]]
        v_u_33:update(p51, p52)
        if v_u_34 and (v_u_35 and v_u_36) then
            v_u_34.CFrame = v_u_35.CFrame:Lerp(v_u_36.CFrame, p52:es_gamelocal_get_audiomanager():get_current_time_ms() / p52:es_gamelocal_get_audiomanager():get_song_length_ms())
        end;
        for _, v53 in v_u_37:key_itr() do
            v53:update(p51)
        end;
    end;
    v_u_2:get_base_fn(v27, "should_do_game_start_zoom_in_effect")
    v27.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 203 ]]
        return true, 49.275000000000006, 16.099999999999998, 0.75;
    end;
    return v27;
end;
return v13;
