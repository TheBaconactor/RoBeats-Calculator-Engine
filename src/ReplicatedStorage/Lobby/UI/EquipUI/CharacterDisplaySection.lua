-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_3 = require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
local v_u_4 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_12 = {
    ["Config"] = {}
}
v_u_12.Config.new = function(_) --[[ Name: new ]] --[[ Line: 19 ]]
    return {
        ["LoadLocalUser"] = true,
        ["CycleOwnedDancesOnClick"] = true,
        ["FillDanceListWithOwnedDances"] = true
    };
end;
v_u_12.new = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_10, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_9, (copy 6): v_u_8, (copy 7): v_u_11, (copy 8): v_u_3, (copy 9): v_u_4, (copy 10): v_u_6, (copy 11): v_u_5, (copy 12): v_u_7 ]]
    local v_u_18 = {}
    if p_u_17 == nil then
        p_u_17 = v_u_12.Config:new()
    end;
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = v_u_10:new()
    local v_u_24 = 1
    local v_u_25 = false
    v_u_18.get_dance_active = function(_) --[[ Name: get_dance_active ]] --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v_u_18.set_dance_active = function(_, p26) --[[ Name: set_dance_active ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        v_u_25 = p26
    end;
    local v_u_27 = Vector3.new(100, 99.75, 100)
    local v_u_28 = 0
    local v_u_29 = 6
    local v_u_30 = 0.75
    local function _(p31) --[[ Name: get_camera_position_for_t ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_29 ]]
        return Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(p31) * v_u_29, 0, math.cos(p31) * -v_u_29);
    end;
    local function _() --[[ Name: update_camera ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_28, (ref 3): v_u_30, (ref 4): v_u_29, (ref 5): v_u_27 ]]
        local v32 = v_u_28
        v_u_21.CFrame = CFrame.new(Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(v32) * v_u_29, 0, math.cos(v32) * -v_u_29), v_u_27)
    end;
    v_u_18.set_camera_focus_offset = function(_, p33) --[[ Name: set_camera_focus_offset ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_21, (ref 3): v_u_28, (ref 4): v_u_30, (ref 5): v_u_29 ]]
        v_u_27 = Vector3.new(100, 100, 100) + p33
        local v34 = v_u_28
        v_u_21.CFrame = CFrame.new(Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(v34) * v_u_29, 0, math.cos(v34) * -v_u_29), v_u_27)
    end;
    v_u_18.set_camera_height = function(_, p35) --[[ Name: set_camera_height ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_21, (ref 3): v_u_28, (ref 4): v_u_29, (ref 5): v_u_27 ]]
        v_u_30 = p35
        local v36 = v_u_28
        v_u_21.CFrame = CFrame.new(Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(v36) * v_u_29, 0, math.cos(v36) * -v_u_29), v_u_27)
    end;
    v_u_18.set_camera_radius = function(_, p37) --[[ Name: set_camera_radius ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_21, (ref 3): v_u_28, (ref 4): v_u_30, (ref 5): v_u_27 ]]
        v_u_29 = p37
        local v38 = v_u_28
        v_u_21.CFrame = CFrame.new(Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(v38) * v_u_29, 0, math.cos(v38) * -v_u_29), v_u_27)
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 78 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_16, (ref 3): v_u_19, (ref 4): p_u_17, (ref 5): v_u_20, (ref 6): v_u_2, (ref 7): v_u_22, (ref 8): v_u_21, (ref 9): v_u_28, (ref 10): v_u_30, (ref 11): v_u_29, (ref 12): v_u_27, (copy 13): v_u_18, (copy 14): p_u_13, (ref 15): v_u_9, (copy 16): v_u_23, (ref 17): v_u_8 ]]
        v_u_1:ptry(function() --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): p_u_16 ]]
            p_u_16.Parent = game.Players.LocalPlayer.PlayerGui
            p_u_16.BackgroundFrame.Visible = false
        end)
        v_u_1:ptry(function() --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): p_u_16, (ref 3): p_u_17, (ref 4): v_u_20, (ref 5): v_u_2, (ref 6): v_u_1 ]]
            v_u_19 = p_u_16.ViewportFrame.WorldModel.Character
            if p_u_17.LoadLocalUser == true then
                v_u_20 = v_u_2:get_character_model_for_playerid(v_u_1:get_local_userid()):Clone()
            else
                v_u_20 = v_u_2:get_default_character_clone()
            end;
            if v_u_20 == nil then
                v_u_20 = v_u_2:get_default_character_clone()
            end;
            v_u_20.Parent = v_u_19.Parent
            v_u_19.Parent = nil
            v_u_20:SetPrimaryPartCFrame(CFrame.new(Vector3.new(100, 100, 100), Vector3.new(100, 100, 99)))
        end)
        v_u_1:ptry(function() --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): p_u_16, (ref 3): v_u_21, (ref 4): v_u_28, (ref 5): v_u_30, (ref 6): v_u_29, (ref 7): v_u_27 ]]
            v_u_22 = p_u_16.ViewportFrame
            v_u_21 = Instance.new("Camera", v_u_22)
            local v39 = v_u_28
            v_u_21.CFrame = CFrame.new(Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(v39) * v_u_29, 0, math.cos(v39) * -v_u_29), v_u_27)
            v_u_22.CurrentCamera = v_u_21
        end)
        v_u_18:set_showing(true)
        local v40 = v_u_9:get_owned_danceid_to_equipped_dict((p_u_13._player_blob_manager:get_player_blob()))
        v_u_23:clear()
        if p_u_17.FillDanceListWithOwnedDances == true then
            for v41, _ in v_u_8:singleton():key_itr() do
                if v40:contains(v41) and v40:get(v41) == true then
                    v_u_23:push_back(v_u_8:singleton():get_dance_animation_for_id(v41))
                end;
            end;
        end;
        v_u_23:shuffle()
    end;
    v_u_18.push_animation_assetid = function(_, p_u_42) --[[ Name: push_animation_assetid ]] --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_23, (ref 3): v_u_24 ]]
        v_u_1:ptry(function() --[[ Line: 125 ]]
            --[[ Upvalues: (copy 1): p_u_42, (ref 2): v_u_23, (ref 3): v_u_24 ]]
            local l_Animation_0 = Instance.new("Animation")
            l_Animation_0.AnimationId = p_u_42
            v_u_23:push_back(l_Animation_0)
            v_u_24 = v_u_23:count()
        end)
    end;
    local v_u_43 = nil
    v_u_18.play_selected_animation = function(_) --[[ Name: play_selected_animation ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_1, (ref 3): v_u_25, (copy 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_20, (ref 7): v_u_11 ]]
        if v_u_43 ~= nil then
            v_u_1:ptry(function() --[[ Line: 136 ]]
                --[[ Upvalues: (ref 1): v_u_43 ]]
                v_u_43:Stop()
            end)
            v_u_43 = nil
        end;
        if v_u_25 then
            local v_u_44 = v_u_23:get(v_u_24)
            if v_u_44 == nil then
                v_u_11:warnf("CharacterDisplaySection _dance_animation_list(%d) no element at index(%d)", v_u_23:count(), v_u_24)
            else
                v_u_1:ptry(function() --[[ Line: 145 ]]
                    --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_20, (ref 3): v_u_44 ]]
                    v_u_43 = v_u_20.Humanoid:LoadAnimation(v_u_44)
                    v_u_43:Play()
                end)
            end;
        end;
    end;
    v_u_18.update_from_playerblob = function(_, p45) --[[ Name: update_from_playerblob ]] --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_20, (ref 3): v_u_2, (ref 4): v_u_1, (ref 5): v_u_4 ]]
        v_u_3:character_modify_with_equipped_data(v_u_20, v_u_2:get_character_model_for_playerid(v_u_1:get_local_userid()), v_u_4:playerblob_get_equipped_info(p45), function() --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            if v_u_20 and v_u_20.PrimaryPart then
                v_u_20.PrimaryPart.Anchored = true
            end;
        end)
    end;
    v_u_18.get_character = function(_) --[[ Name: get_character ]] --[[ Line: 163 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20;
    end;
    v_u_18.get_character_parent = function(_) --[[ Name: get_character_parent ]] --[[ Line: 167 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.Parent;
    end;
    v_u_18.replace_character_model = function(_, p46) --[[ Name: replace_character_model ]] --[[ Line: 171 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20 ]]
        v_u_19 = v_u_20
        v_u_20 = p46
        v_u_20.Parent = v_u_19.Parent
        v_u_19.Parent = nil
        v_u_20:SetPrimaryPartCFrame(CFrame.new(Vector3.new(100, 100, 100), Vector3.new(100, 100, 99)))
    end;
    v_u_18.set_character_visible = function(_, p_u_47) --[[ Name: set_character_visible ]] --[[ Line: 180 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        local function f_r_itr(p48) --[[ Name: r_itr ]] --[[ Line: 181 ]]
            --[[ Upvalues: (copy 1): f_r_itr, (copy 2): p_u_47 ]]
            for _, v49 in pairs(p48:GetChildren()) do
                f_r_itr(v49)
            end;
            if p48:IsA("BasePart") then
                if p_u_47 then
                    p48.Transparency = 0
                else
                    p48.Transparency = 1
                end;
            end;
            if p48:IsA("Decal") then
                if p_u_47 then
                    p48.Transparency = 0
                    return;
                end;
                p48.Transparency = 1
            end;
        end;
        f_r_itr(v_u_20)
    end;
    local v_u_50 = false
    local v_u_51 = Vector2.new()
    v_u_18.behaviour_update = function(p52, p53) --[[ Name: behaviour_update ]] --[[ Line: 205 ]]
        --[[ Upvalues: (copy 1): p_u_13, (copy 2): p_u_14, (copy 3): p_u_15, (ref 4): v_u_6, (ref 5): v_u_50, (ref 6): v_u_51, (ref 7): p_u_17, (ref 8): v_u_5, (ref 9): v_u_25, (ref 10): v_u_24, (copy 11): v_u_23, (ref 12): v_u_28, (ref 13): v_u_21, (ref 14): v_u_30, (ref 15): v_u_29, (ref 16): v_u_27, (ref 17): v_u_7 ]]
        local v54 = 1
        local v55 = false
        if p_u_13._input:get_has_frame_focused_element() ~= true then
            local v56 = p_u_14:get_cursor_nxy()
            if p_u_15:get_nrect(p_u_14):contains_vec2(v56) then
                v54 = 1.1
                if p_u_13._input:control_just_pressed(v_u_6.KEY_CLICK) then
                    v_u_50 = true
                    v_u_51 = v56
                    v55 = true
                end;
                if p_u_17.CycleOwnedDancesOnClick == true and (p_u_13._input:control_just_released(v_u_6.KEY_CLICK) and (v_u_51 - v56).Magnitude < 0.01) then
                    p_u_13._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                    p_u_15:set_scale(1.5)
                    v_u_25 = not v_u_25
                    if v_u_25 then
                        v_u_24 = v_u_24 + 1
                        if v_u_24 > v_u_23:count() then
                            v_u_24 = 1
                        end;
                    end;
                    p52:play_selected_animation()
                end;
            end;
        end;
        if v_u_50 and p_u_13._input:control_pressed(v_u_6.KEY_CLICK) ~= true then
            v_u_50 = false
        end;
        if v_u_50 and v55 ~= true then
            v54 = 1.1
            v_u_28 = v_u_28 + p_u_13._input:get_cursor_delta().X * 0.05
            local v57 = v_u_28
            v_u_21.CFrame = CFrame.new(Vector3.new(100, 100, 100) + Vector3.new(0, v_u_30, 0) + Vector3.new(math.sin(v57) * v_u_29, 0, math.cos(v57) * -v_u_29), v_u_27)
        end;
        p_u_15:set_scale(v_u_7:expt_sec(p_u_15:get_scale(), v54, 0.5, p53))
    end;
    v_u_18.set_showing = function(_, p58) --[[ Name: set_showing ]] --[[ Line: 248 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22.Visible = p58
    end;
    v_u_18.set_alpha = function(_, p59) --[[ Name: set_alpha ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1 ]]
        v_u_22.ImageTransparency = v_u_1:tra(p59)
    end;
    v_u_18.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 256 ]]
        --[[ Upvalues: (copy 1): p_u_16 ]]
        p_u_16:Destroy()
    end;
    v_u_18.layout = function(_) --[[ Name: layout ]] --[[ Line: 260 ]]
        --[[ Upvalues: (copy 1): p_u_15 ]]
        p_u_15:layout()
    end;
    f_cons()
    return v_u_18;
end;
return v_u_12;
