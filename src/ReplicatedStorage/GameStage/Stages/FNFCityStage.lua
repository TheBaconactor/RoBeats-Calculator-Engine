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
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_8 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_11 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_12 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_13 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16 ]]
    v_u_14 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_15 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_16 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
local v17 = {}
local v_u_25 = {
    ["new"] = function(_, p18) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6 ]]
        local v19 = {}
        local l_Train_0 = p18.Train
        local l_CFrame_0 = p18.TrainStart.CFrame
        local l_CFrame_1 = p18.TrainEnd.CFrame
        local v_u_20 = 0
        local v_u_21 = 0
        local v_u_22 = v_u_3:rand_rangef(10, 20)
        local function _() --[[ Name: update_train_position ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): l_Train_0, (copy 2): l_CFrame_0, (copy 3): l_CFrame_1, (ref 4): v_u_20 ]]
            l_Train_0:SetPrimaryPartCFrame(l_CFrame_0:Lerp(l_CFrame_1, v_u_20))
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): l_Train_0, (copy 3): l_CFrame_0, (copy 4): l_CFrame_1 ]]
            v_u_20 = 1
            l_Train_0:SetPrimaryPartCFrame(l_CFrame_0:Lerp(l_CFrame_1, v_u_20))
        end;
        v19.start_anim = function(_) --[[ Name: start_anim ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): l_Train_0, (copy 3): l_CFrame_0, (copy 4): l_CFrame_1 ]]
            v_u_20 = 0
            l_Train_0:SetPrimaryPartCFrame(l_CFrame_0:Lerp(l_CFrame_1, v_u_20))
        end;
        v19.is_finished = function(_) --[[ Name: is_finished ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20 >= 1;
        end;
        v19.should_start_anim = function(_) --[[ Name: should_start_anim ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_22 ]]
            return v_u_22 < v_u_21;
        end;
        v19.update = function(p23, p24) --[[ Name: update ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_20, (ref 3): v_u_6, (copy 4): l_Train_0, (copy 5): l_CFrame_0, (copy 6): l_CFrame_1 ]]
            if p23:is_finished() == true then
                v_u_21 = v_u_21 + v_u_6:TimescaleToDeltaTime(p24)
            else
                v_u_21 = 0
                v_u_20 = v_u_6:move_to(v_u_20, 1, 2.5, p24)
                l_Train_0:SetPrimaryPartCFrame(l_CFrame_0:Lerp(l_CFrame_1, v_u_20))
            end;
        end;
        v_u_20 = 1
        l_Train_0:SetPrimaryPartCFrame(l_CFrame_0:Lerp(l_CFrame_1, v_u_20))
        return v19;
    end
}
v17.new = function(_) --[[ Name: new ]] --[[ Line: 76 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_12, (copy 4): v_u_13, (copy 5): v_u_7, (copy 6): v_u_8, (copy 7): v_u_5, (copy 8): v_u_10, (copy 9): v_u_11, (ref 10): v_u_14, (copy 11): v_u_3, (copy 12): v_u_9, (ref 13): v_u_15, (ref 14): v_u_16, (copy 15): v_u_25, (copy 16): v_u_4 ]]
    local v26 = v_u_1:new()
    v_u_2:get_base_fn(v26, "get_name")
    v26.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 80 ]]
        return "Funkin\' City";
    end;
    v_u_2:get_base_fn(v26, "get_icon")
    v26.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 82 ]]
        return "rbxassetid://10266225796";
    end;
    local v_u_27 = nil
    v26.load_stage = function(_, p_u_28) --[[ Name: load_stage ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_27 ]]
        v_u_12:singleton():load_model_category(v_u_13.GameStage.FNFCityStage, v_u_13.Category.GameStage, function(p29) --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_27, (copy 2): p_u_28 ]]
            v_u_27 = p29
            p_u_28()
        end)
    end;
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = v_u_7:new()
    local v_u_38 = false
    local v_u_39 = v_u_7:new()
    local v_u_40 = nil
    local function f_update_color(p41) --[[ Name: update_color ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_40, (ref 3): v_u_38, (ref 4): v_u_5, (copy 5): v_u_39, (ref 6): v_u_34, (ref 7): v_u_35, (ref 8): v_u_36, (copy 9): v_u_37 ]]
        local v42 = v_u_8:get_server_game_instance_player_powerbar_active(p41._players._slots:get(p41:get_local_game_slot()))
        if v42 ~= v_u_40 then
            v_u_40 = v42
            local v43 = p41:get_game_note_skin_info()
            local v44 = v43:get_slot_basecolor_list(p41:get_local_game_slot())
            local v45 = v43:get_slot_fevercolor_list(p41:get_local_game_slot())
            local v46, v47, v48, v49
            if v42 then
                v46 = v45:get(1):to_color3()
                v47 = v45:get(2):to_color3()
                v48 = v45:get(3):to_color3()
                v49 = v45:get(4):to_color3()
            elseif v_u_38 then
                v46 = v_u_5:new(13, 105, 172):to_color3()
                v47 = v_u_5:new(31, 128, 29):to_color3()
                v48 = v_u_5:new(1, 1, 1):to_color3()
                v49 = v_u_5:new(170, 105, 0):to_color3()
            else
                v46 = v44:get(1):to_color3()
                v47 = v44:get(2):to_color3()
                v48 = v44:get(3):to_color3()
                v49 = v44:get(4):to_color3()
            end;
            v_u_39:clear()
            v_u_39:push_back(v46)
            v_u_39:push_back(v47)
            v_u_39:push_back(v48)
            v_u_39:push_back(v49)
            for v50 = 1, v_u_39:count() do
                local v51 = nil
                if v50 == 1 then
                    v51 = v_u_34
                elseif v50 == 2 then
                    v51 = v_u_35
                elseif v50 == 4 then
                    v51 = v_u_36
                end;
                if v51 then
                    local v52 = v_u_39:get(v50)
                    for _, v53 in v51:key_itr() do
                        v_u_37:push_back({ v53, v52 })
                    end;
                end;
            end;
        end;
    end;
    local function _() --[[ Name: pop_queued_color_change ]] --[[ Line: 156 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        if v_u_37:count() > 0 then
            local v54 = v_u_37:pop_back()
            v54[1].Color = v54[2]
        end;
    end;
    v_u_2:get_base_fn(v26, "setup_stage")
    v26.setup_stage = function(p55, p56) --[[ Name: setup_stage ]] --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_14, (ref 4): v_u_5, (ref 5): v_u_31, (ref 6): v_u_27, (ref 7): v_u_34, (ref 8): v_u_3, (ref 9): v_u_7, (ref 10): v_u_35, (ref 11): v_u_36, (ref 12): v_u_9, (ref 13): v_u_38, (ref 14): v_u_40, (copy 15): f_update_color, (copy 16): v_u_37, (ref 17): v_u_30, (ref 18): v_u_15, (ref 19): v_u_16, (ref 20): v_u_32, (ref 21): v_u_25, (ref 22): v_u_33 ]]
        local v57 = p56._player_settings_manager:get_key(v_u_10.Key.BrightnessSettings) == v_u_11.Dark
        local v58 = v_u_14:get_game_sky()
        v58.SkyboxBk = "rbxassetid://9673625784"
        v58.SkyboxDn = "rbxassetid://10264648518"
        v58.SkyboxFt = "rbxassetid://9673625784"
        v58.SkyboxLf = "rbxassetid://9673625784"
        v58.SkyboxRt = "rbxassetid://9673625784"
        v58.SkyboxUp = "rbxassetid://9673577377"
        local v59 = v_u_14:get_game_lighting()
        v59.Ambient = v_u_5:new(165, 165, 165):to_color3()
        v59.ColorShift_Bottom = v_u_5:new(225, 65, 236):to_color3()
        v59.ColorShift_Top = v_u_5:new(119, 27, 165):to_color3()
        if v57 then
            v59.Brightness = 0.25
        else
            v59.Brightness = 0.75
        end;
        v_u_31 = v_u_27.CenterEmitter
        p55:on_switch_focus_slot(p56)
        v_u_34 = v_u_3:get_list_of_children_of_classname(v_u_27.StadiumDecorations.Buildings, "MeshPart")
        v_u_34:remove_if(function(p60) --[[ Line: 196 ]]
            return p60.Material ~= Enum.Material.Neon;
        end)
        if v57 then
            v_u_7:for_each(v_u_34, function(p61) --[[ Line: 200 ]]
                p61.Transparency = 0.5
            end)
        end;
        local v62 = v_u_3:get_list_of_children_of_classname(v_u_27.TrainA, "MeshPart")
        v62:push_back_from_list((v_u_3:get_list_of_children_of_classname(v_u_27.TrainB, "MeshPart")))
        v62:remove_if(function(p63) --[[ Line: 208 ]]
            return p63.Material ~= Enum.Material.Neon;
        end)
        v_u_35 = v_u_7:new()
        v_u_36 = v_u_7:new()
        for _, v64 in v62:key_itr() do
            if v64:GetAttribute("AltColor") == nil then
                v_u_35:push_back(v64)
            else
                v_u_36:push_back(v64)
            end;
        end;
        local v65 = v_u_9:get_default_base_color_list()
        local v66 = p56:get_game_note_skin_info():get_slot_basecolor_list(p56:get_local_game_slot())
        local v67 = true
        for v68 = 1, v66:count() do
            if v66:get(v68):to_color3() ~= v65:get(v68):to_color3() then
                v67 = false
            end;
        end;
        if v67 then
            v_u_38 = true
        else
            v_u_38 = false
        end;
        v_u_40 = nil
        f_update_color(p56)
        local v69 = 0
        while v_u_37:count() > 0 do
            if v_u_37:count() > 0 then
                local v70 = v_u_37:pop_back()
                v70[1].Color = v70[2]
            end;
            v69 = v69 + 1
            if v69 > 250 then
                break;
            end;
        end;
        v_u_27.Parent = v_u_14:get_local_elements_folder()
        v_u_30 = v_u_15:new(game.ReplicatedStorage.ElementProtos.CharacterShineEffectProto, v_u_16.CHARACTER_POSITION_OFFSET)
        v_u_32 = v_u_25:new(v_u_27.TrainA)
        v_u_33 = v_u_25:new(v_u_27.TrainB)
    end;
    v_u_2:get_base_fn(v26, "on_switch_focus_slot")
    v26.on_switch_focus_slot = function(_, p71) --[[ Name: on_switch_focus_slot ]] --[[ Line: 261 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_4 ]]
        v_u_31:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p71:get_local_game_slot())))
    end;
    v_u_2:get_base_fn(v26, "create_shine_for_slot_at_cframe")
    v26.create_shine_for_slot_at_cframe = function(_, p72, p73, p74) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 269 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        v_u_30:create_shine_for_slot_at_cframe(p72, p73, p74)
    end;
    v_u_2:get_base_fn(v26, "game_update")
    v26.game_update = function(_, p75, p76) --[[ Name: game_update ]] --[[ Line: 274 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_32, (ref 3): v_u_33, (copy 4): f_update_color, (copy 5): v_u_37 ]]
        v_u_30:update(p75, p76)
        v_u_32:update(p75)
        if v_u_32:should_start_anim() then
            v_u_32:start_anim()
        end;
        v_u_33:update(p75)
        if v_u_33:should_start_anim() then
            v_u_33:start_anim()
        end;
        f_update_color(p76)
        if v_u_37:count() > 0 then
            local v77 = v_u_37:pop_back()
            v77[1].Color = v77[2]
        end;
        if v_u_37:count() > 0 then
            local v78 = v_u_37:pop_back()
            v78[1].Color = v78[2]
        end;
        if v_u_37:count() > 0 then
            local v79 = v_u_37:pop_back()
            v79[1].Color = v79[2]
        end;
    end;
    v_u_2:get_base_fn(v26, "teardown_stage")
    v26.teardown_stage = function(_, p80) --[[ Name: teardown_stage ]] --[[ Line: 292 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_27, (ref 3): v_u_32, (ref 4): v_u_33, (ref 5): v_u_34, (ref 6): v_u_35, (ref 7): v_u_36 ]]
        v_u_30:teardown(p80)
        v_u_27:Destroy()
        v_u_32 = nil
        v_u_33 = nil
        v_u_34:clear()
        v_u_35:clear()
        v_u_36:clear()
    end;
    return v26;
end;
return v17;
