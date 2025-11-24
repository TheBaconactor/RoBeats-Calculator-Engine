-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_8 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_11 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_14 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_10, (copy 4): v_u_11, (copy 5): v_u_7, (copy 6): v_u_6, (copy 7): v_u_8, (ref 8): v_u_12, (copy 9): v_u_5, (copy 10): v_u_3, (copy 11): v_u_9, (ref 12): v_u_13, (ref 13): v_u_14, (copy 14): v_u_4 ]]
        local v15 = v_u_1:new()
        v_u_2:get_base_fn(v15, "get_name")
        v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 32 ]]
            return "Neon City";
        end;
        v_u_2:get_base_fn(v15, "get_icon")
        v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 34 ]]
            return "rbxassetid://9659667203";
        end;
        local v_u_16 = nil
        v15.load_stage = function(_, p_u_17) --[[ Name: load_stage ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_16 ]]
            v_u_10:singleton():load_model_category(v_u_11.GameStage.NeonCityStage, v_u_11.Category.GameStage, function(p18) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_17 ]]
                v_u_16 = p18
                p_u_17()
            end)
        end;
        local v_u_19 = nil
        local v_u_20 = v_u_7:new()
        local v_u_21 = v_u_6:new()
        local v_u_22 = false
        local v_u_23 = v_u_6:new()
        local v_u_24 = nil
        local function f_update_color(p25) --[[ Name: update_color ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_24, (ref 3): v_u_22, (copy 4): v_u_23, (copy 5): v_u_20, (copy 6): v_u_21 ]]
            local v26 = v_u_8:get_server_game_instance_player_powerbar_active(p25._players._slots:get(p25:get_local_game_slot()))
            if v26 ~= v_u_24 then
                v_u_24 = v26
                local v27 = p25:get_game_note_skin_info()
                local v28 = v27:get_slot_basecolor_list(p25:get_local_game_slot())
                local v29 = v27:get_slot_fevercolor_list(p25:get_local_game_slot())
                local v30, v31, v32, v33
                if v26 then
                    v30 = v29:get(1):to_color3()
                    v31 = v29:get(2):to_color3()
                    v32 = v29:get(3):to_color3()
                    v33 = v29:get(4):to_color3()
                elseif v_u_22 then
                    v30 = Color3.new(1, 0.498039, 0.498039)
                    v31 = Color3.new(0.498039, 1, 0.498039)
                    v32 = Color3.new(0.498039, 0.498039, 1)
                    v33 = Color3.new(1, 1, 1)
                else
                    v30 = v28:get(1):to_color3()
                    v31 = v28:get(2):to_color3()
                    v32 = v28:get(3):to_color3()
                    v33 = v28:get(4):to_color3()
                end;
                v_u_23:clear()
                v_u_23:push_back(v30)
                v_u_23:push_back(v31)
                v_u_23:push_back(v32)
                v_u_23:push_back(v33)
                for v34 = 1, v_u_23:count() do
                    local v35 = v_u_20:list_of(v34)
                    local v36 = v_u_23:get(v34)
                    for _, v37 in v35:key_itr() do
                        v_u_21:push_back({ v37, v36 })
                    end;
                end;
            end;
        end;
        local function _() --[[ Name: pop_queued_color_change ]] --[[ Line: 93 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            if v_u_21:count() > 0 then
                local v38 = v_u_21:pop_back()
                v38[1].Color = v38[2]
            end;
        end;
        local v_u_39 = nil
        v_u_2:get_base_fn(v15, "setup_stage")
        v15.setup_stage = function(p40, p41) --[[ Name: setup_stage ]] --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_12, (ref 3): v_u_5, (copy 4): v_u_20, (copy 5): v_u_21, (ref 6): v_u_3, (ref 7): v_u_7, (ref 8): v_u_24, (ref 9): v_u_9, (ref 10): v_u_22, (copy 11): f_update_color, (ref 12): v_u_19, (ref 13): v_u_39, (ref 14): v_u_13, (ref 15): v_u_14 ]]
            v_u_16.Parent = v_u_12:get_local_elements_folder()
            local v42 = v_u_12:get_game_lighting()
            v42.Brightness = 1
            v42.Ambient = v_u_5:new(0, 0, 0):to_color3()
            v42.ColorShift_Bottom = v_u_5:new(60, 4, 68):to_color3()
            v42.ColorShift_Top = v_u_5:new(113, 9, 139):to_color3()
            v42.OutdoorAmbient = v_u_5:new(109, 80, 124):to_color3()
            v42.ClockTime = 6.2
            v42.FogColor = v_u_5:new(16, 5, 61):to_color3()
            v42.FogEnd = 175
            v42.FogStart = 25
            v_u_20:clear()
            v_u_21:clear()
            local v43 = v_u_3:get_list_of_children_of_classname(v_u_16.City, "MeshPart")
            v43:remove_if(function(p44) --[[ Line: 122 ]]
                return p44.Material ~= Enum.Material.Neon;
            end)
            local v45 = v_u_7:new()
            for _, v46 in v43:key_itr() do
                v45:push_back_to(tostring(v46.Color), v46)
            end;
            local v47 = 1
            for _, v48 in v45:key_itr() do
                v_u_20:list_of(v47):push_back_from_list(v48)
                v47 = v47 + 1
                if v47 > 4 then
                    v47 = 1
                end;
            end;
            local v49 = v_u_3:get_list_of_children_of_classname(v_u_16.CenterEmitter, "Part")
            v49:remove_if(function(p50) --[[ Line: 142 ]]
                return p50.Material ~= Enum.Material.Neon;
            end)
            for _, v51 in v49:key_itr() do
                v_u_20:list_of(v_u_3:rand_rangei(1, 5)):push_back(v51)
            end;
            v_u_24 = nil
            local v52 = v_u_9:get_default_base_color_list()
            local v53 = p41:get_game_note_skin_info():get_slot_basecolor_list(p41:get_local_game_slot())
            local v54 = true
            for v55 = 1, v53:count() do
                if v53:get(v55):to_color3() ~= v52:get(v55):to_color3() then
                    v54 = false
                end;
            end;
            if v54 then
                v_u_22 = true
            else
                v_u_22 = false
            end;
            f_update_color(p41)
            local v56 = 0
            while v_u_21:count() > 0 do
                if v_u_21:count() > 0 then
                    local v57 = v_u_21:pop_back()
                    v57[1].Color = v57[2]
                end;
                v56 = v56 + 1
                if v56 > 250 then
                    break;
                end;
            end;
            v_u_19 = v_u_16.FaceToPlayer
            p40:on_switch_focus_slot(p41)
            v_u_39 = v_u_13:new(game.ReplicatedStorage.ElementProtos.CharacterShineEffectProto, v_u_14.CHARACTER_POSITION_OFFSET)
        end;
        v_u_2:get_base_fn(v15, "on_switch_focus_slot")
        v15.on_switch_focus_slot = function(_, p58) --[[ Name: on_switch_focus_slot ]] --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_4 ]]
            v_u_19:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p58:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v15, "teardown_stage")
        v15.teardown_stage = function(_, p59) --[[ Name: teardown_stage ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_39, (copy 2): v_u_20, (copy 3): v_u_21, (ref 4): v_u_19, (ref 5): v_u_16 ]]
            v_u_39:teardown(p59)
            v_u_20:clear()
            v_u_21:clear()
            v_u_19 = nil
            v_u_16:Destroy()
        end;
        v_u_2:get_base_fn(v15, "create_shine_for_slot_at_cframe")
        v15.create_shine_for_slot_at_cframe = function(_, p60, p61, p62) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            v_u_39:create_shine_for_slot_at_cframe(p60, p61, p62)
        end;
        v_u_2:get_base_fn(v15, "game_update")
        v15.game_update = function(_, p63, p64) --[[ Name: game_update ]] --[[ Line: 212 ]]
            --[[ Upvalues: (ref 1): v_u_39, (copy 2): f_update_color, (copy 3): v_u_21 ]]
            v_u_39:update(p63, p64)
            f_update_color(p64)
            if v_u_21:count() > 0 then
                local v65 = v_u_21:pop_back()
                v65[1].Color = v65[2]
            end;
            if v_u_21:count() > 0 then
                local v66 = v_u_21:pop_back()
                v66[1].Color = v66[2]
            end;
            if v_u_21:count() > 0 then
                local v67 = v_u_21:pop_back()
                v67[1].Color = v67[2]
            end;
        end;
        v_u_2:get_base_fn(v15, "should_do_game_start_zoom_in_effect")
        v15.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 222 ]]
            return true, 45.625, 21, 0.75;
        end;
        return v15;
    end
};
