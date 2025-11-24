-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.PowerBarState)
local _ = game:GetService("HttpService")
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = {
    ["CrowdElement"] = {}
}
v_u_6.CrowdElement.new = function(_, p_u_7, p_u_8, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_6 ]]
    local v11 = {
        ["_anim_ct"] = 0
    }
    local v_u_12 = nil
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    v11.cons = function(_) --[[ Name: cons ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_8, (ref 3): v_u_15, (ref 4): v_u_1, (ref 5): p_u_9, (ref 6): v_u_4, (ref 7): p_u_10, (ref 8): v_u_13, (ref 9): v_u_14 ]]
        v_u_12 = p_u_8:Clone()
        v_u_15 = v_u_12.Panel.SurfaceGui.ImageLabel
        local v16 = v_u_1:rand_rangei(1, 5)
        if v16 == 1 then
            v_u_15.Image = "rbxassetid://698489474"
        elseif v16 == 2 then
            v_u_15.Image = "rbxassetid://698514062"
        elseif v16 == 3 then
            v_u_15.Image = "rbxassetid://698514043"
        else
            v_u_15.Image = "rbxassetid://698514063"
        end;
        v_u_12.PrimaryPart.CFrame = CFrame.new(p_u_9.Position + Vector3.new(0, 3.5, 0) + Vector3.new(v_u_1:rand_rangef(-1.5, 1.5), 0, v_u_1:rand_rangef(-1.5, 1.5)), v_u_4._world_center_position)
        v_u_12.Parent = p_u_10
        v_u_13 = v_u_12.PrimaryPart.Position
        v_u_14 = v_u_12.PrimaryPart.Rotation
    end;
    v11.set_userid = function(_, p17) --[[ Name: set_userid ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_1, (ref 3): v_u_15 ]]
        v_u_12.Panel.Size = Vector3.new(9, 9, 0.5)
        v_u_1:get_user_thumbnail(p17, function(p18, p19) --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            if p19 == true then
                v_u_15.Image = p18
            end;
        end, false, Enum.ThumbnailType.AvatarThumbnail, Enum.ThumbnailSize.Size180x180)
    end;
    v11.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_7, (ref 3): p_u_8, (ref 4): p_u_9, (ref 5): p_u_10 ]]
        v_u_12:Destroy()
        p_u_7 = nil
        p_u_8 = nil
        p_u_9 = nil
        p_u_10 = nil
    end;
    v11.update = function(p20, p21, p22) --[[ Name: update ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_15, (ref 3): v_u_6 ]]
        if p22:show_fullscreen_mobile_ui() then
            return;
        elseif p20._anim_ct > 0 then
            p20._anim_ct = p20._anim_ct - 0.066 * p21
            v_u_15.Position = UDim2.new(0, 0, 0, v_u_6:cached_curve_value(p20._anim_ct) * -30)
        end;
    end;
    v11:cons()
    return v11;
end;
local v_u_23 = {}
v_u_6.cached_curve_value = function(_, p24) --[[ Name: cached_curve_value ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): v_u_23, (copy 2): v_u_3 ]]
    local v25 = math.floor(p24 * 100)
    if v_u_23[v25] == nil then
        v_u_23[v25] = v_u_3:BezierPt2ForT(0, 0, 1, 0, 1, 0, 1, 2, p24).Y
    end;
    return v_u_23[v25];
end;
local v_u_26 = true
v_u_6.new = function(_, p_u_27) --[[ Name: new ]] --[[ Line: 107 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (ref 3): v_u_26, (copy 4): v_u_1, (copy 5): v_u_3, (copy 6): v_u_5 ]]
    local v28 = {
        ["cons"] = function(_) end
    }
    local v_u_29 = v_u_2:new()
    v28.load_crowd = function(_, p30) --[[ Name: load_crowd ]] --[[ Line: 114 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_6, (ref 3): v_u_29 ]]
        for _, v31 in pairs(p_u_27.Row1Anchors:GetChildren()) do
            v_u_29:push_back((v_u_6.CrowdElement:new(p30, game.ReplicatedStorage.ElementProtos.CrowdFillin, v31, p_u_27.Elements)))
        end;
        for _, v32 in pairs(p_u_27.Row2Anchors:GetChildren()) do
            v_u_29:push_back((v_u_6.CrowdElement:new(p30, game.ReplicatedStorage.ElementProtos.CrowdFillin, v32, p_u_27.Elements)))
        end;
    end;
    local v_u_33 = false
    v28.has_loaded_friends = function(_) --[[ Name: has_loaded_friends ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    v28.load_friends_into_crowd = function(p_u_34) --[[ Name: load_friends_into_crowd ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_29, (ref 3): v_u_26, (ref 4): v_u_1 ]]
        v_u_33 = true
        spawn(function() --[[ Line: 145 ]]
            --[[ Upvalues: (copy 1): p_u_34, (ref 2): v_u_29, (ref 3): v_u_26, (ref 4): v_u_1 ]]
            local v_u_35 = nil
            pcall(function() --[[ Line: 147 ]]
                --[[ Upvalues: (ref 1): v_u_35 ]]
                v_u_35 = game.Players:GetFriendsAsync(game.Players.LocalPlayer.UserId)
            end)
            if v_u_35 == nil then
                return;
            end;
            local v36 = v_u_35
            while p_u_34 ~= nil do
                for _, v37 in pairs((v36:GetCurrentPage())) do
                    if v_u_29 == nil then
                        return;
                    end;
                    if v_u_26 ~= true then
                        return;
                    end;
                    v_u_29:get((v_u_1:rand_rangei(1, v_u_29:count()))):set_userid(v37.Id)
                    wait(0.1)
                end;
                if v36.IsFinished then
                    break;
                end;
                v36:AdvanceToNextPageAsync()
            end;
        end)
    end;
    v28.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        for v38 = 1, v_u_29:count() do
            v_u_29:get(v38):teardown()
        end;
        v_u_29:clear()
        v_u_29 = nil
    end;
    local v_u_39 = nil
    local v_u_40 = 0
    local v_u_41 = 1.5
    local v_u_42 = 1
    v28.update = function(_, p43, p44) --[[ Name: update ]] --[[ Line: 187 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_26, (ref 3): v_u_39, (ref 4): v_u_3, (ref 5): v_u_41, (ref 6): v_u_40, (ref 7): v_u_5, (ref 8): v_u_29, (ref 9): v_u_42 ]]
        v_u_1:profilebegin("CrowdManager:update")
        if v_u_26 and p44:es_gamelocal_get_audiomanager():is_playing() then
            if v_u_39 == nil then
                v_u_39 = tick()
            end;
            local v45 = tick()
            local v46 = v_u_3:DeltaTimeToTimescale(v45 - v_u_39)
            if v46 > 2.5 and v_u_41 > 1.5 then
                v_u_40 = v_u_40 + 1
                v_u_41 = 0
                if v_u_40 > 10 then
                    v_u_26 = false
                    v_u_5:warnf("Multiple slow frames detected, disabling crowd(%.2f)", v46)
                end;
            end;
            v_u_41 = v_u_41 + v_u_3:TimescaleToDeltaTime(p43)
            v_u_39 = v45
        end;
        if v_u_26 then
            local v47 = math.floor(v_u_29:count() / 3)
            for v48 = 1, v47 do
                local v49 = v_u_42 + v48
                if v49 < v_u_29:count() then
                    v_u_29:get(v49):update(p43 * 3, p44)
                end;
            end;
            v_u_42 = v_u_42 + v47
            if v_u_42 > v_u_29:count() then
                v_u_42 = 0
            end;
            local v50 = p44:es_gamelocal_get_audiomanager():is_beat()
            local v51 = p44:es_gamelocal_get_scoremanager():display_powerbar_active() == true
            for v52 = 1, v_u_29:count() do
                if v51 then
                    if v50 then
                        v_u_29:get(v52)._anim_ct = 1
                    end;
                elseif v_u_1:rand_rangei(0, 50) < 1 then
                    v_u_29:get(v52)._anim_ct = 1
                end;
            end;
        end;
        v_u_1:profileend()
    end;
    v28:cons()
    return v28;
end;
return v_u_6;
