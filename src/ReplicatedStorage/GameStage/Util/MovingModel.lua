-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.Override)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v5 = {}
local v_u_6 = {
    ["EaseInOut"] = 1,
    ["Linear"] = 2,
    ["Instant"] = 3,
    ["EaseIn"] = 4,
    ["EaseOut"] = 5
}
v5.new = function(_, p_u_7) --[[ Name: new ]] --[[ Line: 29 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_2 ]]
    local v8 = {}
    local l_Asset_0 = p_u_7.Asset
    local v_u_9 = v_u_3:new()
    local v_u_10 = v_u_3:new()
    local v_u_11 = v_u_3:new()
    local v_u_12 = v_u_3:new()
    local v_u_13 = v_u_3:new()
    local v_u_14 = 1
    local v_u_15 = CFrame.new()
    local v_u_16 = CFrame.new()
    local v_u_17 = 0
    local v_u_18 = 0
    local v_u_19 = 1
    local v_u_20 = 0
    local l_EaseInOut_0 = v_u_6.EaseInOut
    local function _() --[[ Name: update_pos ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): l_Asset_0, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_17 ]]
        l_Asset_0:SetPrimaryPartCFrame(v_u_15:Lerp(v_u_16, v_u_17))
    end;
    local function _() --[[ Name: increment_anchor_index ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_9 ]]
        v_u_14 = v_u_14 + 1
        if v_u_14 > v_u_9:count() then
            v_u_14 = 1
        end;
    end;
    local function f_start_animation_at_anchor_index() --[[ Name: start_animation_at_anchor_index ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_14, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_17, (ref 6): v_u_18, (ref 7): v_u_19, (copy 8): v_u_10, (ref 9): v_u_20, (copy 10): v_u_11, (ref 11): v_u_1, (copy 12): v_u_12, (ref 13): l_EaseInOut_0, (copy 14): v_u_13 ]]
        if v_u_9:count() ~= 0 then
            if v_u_14 > v_u_9:count() then
                v_u_14 = 1
            end;
            v_u_15 = v_u_9:get(v_u_14)
            v_u_16 = v_u_9:get(v_u_14)
            if v_u_14 + 1 <= v_u_9:count() then
                v_u_16 = v_u_9:get(v_u_14 + 1)
            else
                v_u_16 = v_u_9:get(1)
            end;
            v_u_17 = 0
            v_u_18 = 0
            v_u_19 = v_u_10:get(v_u_14)
            v_u_20 = v_u_11:get(v_u_14) + v_u_1:rand_rangef(0, v_u_12:get(v_u_14))
            l_EaseInOut_0 = v_u_13:get(v_u_14)
        end;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_7, (copy 3): v_u_9, (copy 4): v_u_10, (copy 5): v_u_11, (copy 6): v_u_12, (copy 7): v_u_13, (ref 8): v_u_6, (copy 9): f_start_animation_at_anchor_index, (copy 10): l_Asset_0, (ref 11): v_u_15, (ref 12): v_u_16, (ref 13): v_u_17 ]]
        local v21 = v_u_4:new()
        for _, v22 in pairs(p_u_7.Anchors:GetChildren()) do
            v21:add(v22.Name, v22)
        end;
        local v23 = v21:key_list()
        v23:sort(function(p24, p25) --[[ Line: 87 ]]
            return p24 < p25;
        end)
        v_u_9:clear()
        v_u_10:clear()
        v_u_11:clear()
        v_u_12:clear()
        for _, v26 in v23:key_itr() do
            local v27 = v21:get(v26)
            v_u_9:push_back(v27.CFrame)
            local v28 = v27:FindFirstChild("Duration")
            if v28 then
                v_u_10:push_back(v28.Value)
            else
                v_u_10:push_back(5)
            end;
            local v29 = v27:FindFirstChild("Wait")
            if v29 then
                v_u_11:push_back(v29.Value)
            else
                v_u_11:push_back(0)
            end;
            local v30 = v27:FindFirstChild("WaitRandom")
            if v30 then
                v_u_12:push_back(v30.Value)
            else
                v_u_12:push_back(0)
            end;
            local v31 = v27:FindFirstChild("Ease")
            if v31 then
                if v31.Value == "Linear" then
                    v_u_13:push_back(v_u_6.Linear)
                elseif v31.Value == "Instant" then
                    v_u_13:push_back(v_u_6.Instant)
                elseif v31.Value == "EaseIn" then
                    v_u_13:push_back(v_u_6.EaseIn)
                elseif v31.Value == "EaseOut" then
                    v_u_13:push_back(v_u_6.EaseOut)
                else
                    v_u_13:push_back(v_u_6.EaseInOut)
                end;
            else
                v_u_13:push_back(v_u_6.EaseInOut)
            end;
        end;
        f_start_animation_at_anchor_index()
        l_Asset_0:SetPrimaryPartCFrame(v_u_15:Lerp(v_u_16, v_u_17))
    end;
    v8.update = function(_, p32) --[[ Name: update ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_2, (ref 3): v_u_18, (ref 4): v_u_19, (ref 5): l_EaseInOut_0, (ref 6): v_u_6, (ref 7): v_u_17, (ref 8): v_u_14, (copy 9): v_u_9, (copy 10): f_start_animation_at_anchor_index, (copy 11): l_Asset_0, (ref 12): v_u_15, (ref 13): v_u_16 ]]
        if v_u_20 > 0 then
            v_u_20 = v_u_20 - v_u_2:TimescaleToDeltaTime(p32)
        else
            v_u_18 = v_u_2:IncrementClamp(v_u_18, v_u_2:TimescaleToDeltaTime(p32), 0, v_u_19)
            if l_EaseInOut_0 == v_u_6.EaseInOut then
                v_u_17 = v_u_2:BezierYForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_18 / v_u_19)
            elseif l_EaseInOut_0 == v_u_6.Instant then
                v_u_17 = 0
            elseif l_EaseInOut_0 == v_u_6.EaseIn then
                v_u_17 = v_u_2:BezierYForT(0, 0, 1, 0, 1, 1, 1, 1, v_u_18 / v_u_19)
            elseif l_EaseInOut_0 == v_u_6.EaseOut then
                v_u_17 = v_u_2:BezierYForT(0, 0, 0, 1, 1, 1, 1, 1, v_u_18 / v_u_19)
            else
                v_u_17 = v_u_18 / v_u_19
            end;
            if v_u_19 <= v_u_18 then
                v_u_14 = v_u_14 + 1
                if v_u_14 > v_u_9:count() then
                    v_u_14 = 1
                end;
                f_start_animation_at_anchor_index()
            end;
            l_Asset_0:SetPrimaryPartCFrame(v_u_15:Lerp(v_u_16, v_u_17))
        end;
    end;
    v8.reset_to_default_position = function(_) --[[ Name: reset_to_default_position ]] --[[ Line: 196 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): l_Asset_0 ]]
        if v_u_9:count() > 0 then
            l_Asset_0:SetPrimaryPartCFrame(v_u_9:get(1))
        end;
    end;
    v8.recalc_positions = function(_) --[[ Name: recalc_positions ]] --[[ Line: 202 ]]
        --[[ Upvalues: (copy 1): f_cons ]]
        f_cons()
    end;
    f_cons()
    return v8;
end;
return v5;
