-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_10 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_11 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_15 ]]
    v_u_13 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_14 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_15 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_9, (copy 6): v_u_8, (copy 7): v_u_10, (copy 8): v_u_12, (ref 9): v_u_13, (copy 10): v_u_3, (copy 11): v_u_11, (ref 12): v_u_14, (copy 13): v_u_4, (copy 14): v_u_7 ]]
        local v16 = v_u_1:new()
        v_u_2:get_base_fn(v16, "get_name")
        v16.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 35 ]]
            return "Cryptic Citadel";
        end;
        v_u_2:get_base_fn(v16, "get_icon")
        v16.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 37 ]]
            return "rbxassetid://17850264469";
        end;
        local v_u_17 = nil
        v16.load_stage = function(_, p_u_18) --[[ Name: load_stage ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_17 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.CastleStage, v_u_6.Category.GameStage, function(p19) --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_17, (copy 2): p_u_18 ]]
                v_u_17 = p19
                p_u_18()
            end)
        end;
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = v_u_9:new()
        local v_u_24 = v_u_8:new()
        local v_u_25 = false
        local v_u_26 = v_u_8:new()
        local v_u_27 = nil
        local function f_update_color(p28) --[[ Name: update_color ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_27, (ref 3): v_u_25, (copy 4): v_u_26, (copy 5): v_u_23, (copy 6): v_u_24 ]]
            local v29 = v_u_10:get_server_game_instance_player_powerbar_active(p28._players._slots:get(p28:get_local_game_slot()))
            if v29 ~= v_u_27 then
                v_u_27 = v29
                local v30 = p28:get_game_note_skin_info()
                local v31 = v30:get_slot_basecolor_list(p28:get_local_game_slot())
                local v32 = v30:get_slot_fevercolor_list(p28:get_local_game_slot())
                local v33, v34, v35, v36
                if v29 then
                    v33 = v32:get(1):to_color3()
                    v34 = v32:get(2):to_color3()
                    v35 = v32:get(3):to_color3()
                    v36 = v32:get(4):to_color3()
                elseif v_u_25 then
                    v33 = Color3.new(0.8352941274642944, 0.45098039507865906, 0.239215686917305)
                    v34 = Color3.new(0.8352941274642944, 0.45098039507865906, 0.239215686917305)
                    v35 = Color3.new(0.8352941274642944, 0.45098039507865906, 0.239215686917305)
                    v36 = Color3.new(0.8352941274642944, 0.45098039507865906, 0.239215686917305)
                else
                    v33 = v31:get(1):to_color3()
                    v34 = v31:get(2):to_color3()
                    v35 = v31:get(3):to_color3()
                    v36 = v31:get(4):to_color3()
                end;
                v_u_26:clear()
                v_u_26:push_back(v33)
                v_u_26:push_back(v34)
                v_u_26:push_back(v35)
                v_u_26:push_back(v36)
                for v37 = 1, v_u_26:count() do
                    local v38 = v_u_23:list_of(v37)
                    local v39 = v_u_26:get(v37)
                    for _, v40 in v38:key_itr() do
                        v_u_24:push_back({ v40, v39 })
                    end;
                end;
            end;
        end;
        local function _() --[[ Name: pop_queued_color_change ]] --[[ Line: 99 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            if v_u_24:count() > 0 then
                local v41 = v_u_24:pop_back()
                v41[1].Color = v41[2]
            end;
        end;
        local v_u_42 = Color3.new(0.498039, 0.498039, 0.498039)
        local v_u_43 = Color3.new(0.3137255012989044, 0.5411764979362488, 0.6235294342041016)
        local v_u_44 = v_u_12:new()
        local v_u_45 = nil
        local v_u_46 = 0
        local v_u_47 = nil
        v_u_2:get_base_fn(v16, "setup_stage")
        v16.setup_stage = function(p48, p49) --[[ Name: setup_stage ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_13, (copy 3): v_u_42, (copy 4): v_u_44, (ref 5): v_u_22, (copy 6): v_u_23, (copy 7): v_u_24, (ref 8): v_u_3, (ref 9): v_u_9, (ref 10): v_u_27, (ref 11): v_u_11, (ref 12): v_u_25, (copy 13): f_update_color, (ref 14): v_u_20, (ref 15): v_u_45, (ref 16): v_u_46, (ref 17): v_u_47, (ref 18): v_u_21, (ref 19): v_u_14 ]]
            v_u_17.Parent = v_u_13:get_local_elements_folder()
            local v50 = v_u_13:get_game_sky()
            v50.SkyboxBk = "rbxassetid://14042163127"
            v50.SkyboxDn = "rbxassetid://14042167610"
            v50.SkyboxFt = "rbxassetid://14042168960"
            v50.SkyboxLf = "rbxassetid://14042170362"
            v50.SkyboxRt = "rbxassetid://14042171912"
            v50.SkyboxUp = "rbxassetid://14042172947"
            local v51 = v_u_13:get_game_lighting()
            v51.Ambient = Color3.new(0, 0, 0)
            v51.Brightness = 0
            v51.ColorShift_Bottom = Color3.new(0, 0, 0.498039)
            v51.ColorShift_Top = Color3.new(0.203922, 0.164706, 0.647059)
            v51.OutdoorAmbient = v_u_42
            v_u_44:set(v_u_42.R, v_u_42.G, v_u_42.B)
            v51.ClockTime = 12
            v51.GeographicLatitude = 45
            v_u_22 = v51
            v_u_23:clear()
            v_u_24:clear()
            local v52 = v_u_3:get_list_of_children_of_classname(v_u_17.FaceToPlayer, "Part")
            v52:remove_if(function(p53) --[[ Line: 147 ]]
                return p53.Material ~= Enum.Material.Neon;
            end)
            local v54 = v_u_9:new()
            local v55 = 1
            for _, v56 in v52:key_itr() do
                v54:push_back_to(v55, v56)
                v55 = v55 + 1
                if v55 > 4 then
                    v55 = 1
                end;
            end;
            local v57 = 1
            for _, v58 in v54:key_itr() do
                v_u_23:list_of(v57):push_back_from_list(v58)
                v57 = v57 + 1
                if v57 > 4 then
                    v57 = 1
                end;
            end;
            v_u_27 = nil
            local v59 = v_u_11:get_default_base_color_list()
            local v60 = p49:get_game_note_skin_info():get_slot_basecolor_list(p49:get_local_game_slot())
            local v61 = true
            for v62 = 1, v60:count() do
                if v60:get(v62):to_color3() ~= v59:get(v62):to_color3() then
                    v61 = false
                end;
            end;
            if v61 then
                v_u_25 = true
            else
                v_u_25 = false
            end;
            f_update_color(p49)
            local v63 = 0
            while v_u_24:count() > 0 do
                if v_u_24:count() > 0 then
                    local v64 = v_u_24:pop_back()
                    v64[1].Color = v64[2]
                end;
                v63 = v63 + 1
                if v63 > 250 then
                    break;
                end;
            end;
            v_u_20 = v_u_17.FaceToPlayer
            v_u_45 = v_u_20.Spotlight.Mesh
            v_u_45.Transparency = v_u_3:tra(0)
            v_u_46 = 0
            p48:on_switch_focus_slot(p49)
            v_u_47 = v_u_17.CharacterShineProto
            v_u_47.Parent = nil
            v_u_21 = v_u_14:new(v_u_47, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v16, "on_switch_focus_slot")
        v16.on_switch_focus_slot = function(_, p65) --[[ Name: on_switch_focus_slot ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_4 ]]
            v_u_20:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p65:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v16, "teardown_stage")
        v16.teardown_stage = function(_, p66) --[[ Name: teardown_stage ]] --[[ Line: 223 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_22, (ref 3): v_u_45, (ref 4): v_u_47, (ref 5): v_u_21, (copy 6): v_u_23, (copy 7): v_u_24, (ref 8): v_u_17 ]]
            v_u_20 = nil
            v_u_22 = nil
            v_u_45 = nil
            v_u_47:Destroy()
            v_u_21:teardown(p66)
            v_u_23:clear()
            v_u_24:clear()
            v_u_17:Destroy()
        end;
        v_u_2:get_base_fn(v16, "create_shine_for_slot_at_cframe")
        v16.create_shine_for_slot_at_cframe = function(_, p67, p68, p69) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:create_shine_for_slot_at_cframe(p67, p68, p69)
        end;
        local v_u_70 = v_u_12:new()
        v_u_2:get_base_fn(v16, "game_update")
        v16.game_update = function(_, p71, p72) --[[ Name: game_update ]] --[[ Line: 243 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): f_update_color, (copy 3): v_u_24, (ref 4): v_u_10, (copy 5): v_u_44, (ref 6): v_u_7, (copy 7): v_u_43, (copy 8): v_u_42, (copy 9): v_u_70, (ref 10): v_u_22, (ref 11): v_u_45, (ref 12): v_u_46, (ref 13): v_u_3 ]]
            v_u_21:update(p71, p72)
            f_update_color(p72)
            if v_u_24:count() > 0 then
                local v73 = v_u_24:pop_back()
                v73[1].Color = v73[2]
            end;
            if v_u_24:count() > 0 then
                local v74 = v_u_24:pop_back()
                v74[1].Color = v74[2]
            end;
            if v_u_24:count() > 0 then
                local v75 = v_u_24:pop_back()
                v75[1].Color = v75[2]
            end;
            local v76 = 0
            if v_u_10:get_server_game_instance_player_powerbar_active(p72._players._slots:get(p72:get_local_game_slot())) then
                v_u_44:set(v_u_7:expt_sec(v_u_44._x, v_u_43.R, 1.5, p71), v_u_7:expt_sec(v_u_44._y, v_u_43.G, 1.5, p71), v_u_7:expt_sec(v_u_44._z, v_u_43.B, 1.5, p71))
                v76 = 0.025
            else
                v_u_44:set(v_u_7:expt_sec(v_u_44._x, v_u_42.R, 1.5, p71), v_u_7:expt_sec(v_u_44._y, v_u_42.G, 1.5, p71), v_u_7:expt_sec(v_u_44._z, v_u_42.B, 1.5, p71))
            end;
            v_u_70:set(v_u_22.OutdoorAmbient.R, v_u_22.OutdoorAmbient.G, v_u_22.OutdoorAmbient.B)
            if v_u_44:distance_to(v_u_70) > 0.001 then
                v_u_22.OutdoorAmbient = Color3.new(v_u_44._x, v_u_44._y, v_u_44._z)
            end;
            if v_u_45 then
                v_u_46 = v_u_7:expt_sec(v_u_46, v76, 1, p71)
                v_u_45.Transparency = v_u_3:tra(v_u_46)
            end;
        end;
        v16.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 281 ]]
            return true, 48.75, 17, 0.9375;
        end;
        return v16;
    end
};
