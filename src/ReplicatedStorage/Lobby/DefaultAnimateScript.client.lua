-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local v_u_1 = nil
local function _(p2, p3) --[[ Name: humanoid_load_animation ]] --[[ Line: 2 ]]
    --[[ Upvalues: (ref 1): v_u_1 ]]
    v_u_1 = p3
    local v4 = p2:FindFirstChild("Animator")
    if v4 then
        return v4:LoadAnimation(p3);
    else
        return nil;
    end;
end;
local l_Parent_0 = script.Parent
local v_u_9 = (function(p5, p6) --[[ Name: waitForChild ]] --[[ Line: 11 ]]
    local v7 = p5:findFirstChild(p6)
    if v7 then
        return v7;
    end;
    repeat
        local v8 = p5.ChildAdded:wait()
    until v8.Name == p6;
    return v8;
end)(l_Parent_0, "Humanoid")
local v_u_10 = {}
local v_u_11 = {
    ["idle"] = {},
    ["walk"] = {},
    ["run"] = {},
    ["swim"] = {},
    ["swimidle"] = {},
    ["jump"] = {},
    ["fall"] = {},
    ["climb"] = {},
    ["sit"] = {},
    ["wave"] = {},
    ["point"] = {},
    ["dance"] = {},
    ["dance2"] = {},
    ["dance3"] = {},
    ["laugh"] = {},
    ["cheer"] = {}
}
math.randomseed(tick())
local function f_configureAnimationSet(p_u_12, p_u_13) --[[ Name: configureAnimationSet ]] --[[ Line: 97 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): f_configureAnimationSet ]]
    if v_u_10[p_u_12] ~= nil then
        for _, v14 in pairs(v_u_10[p_u_12].connections) do
            v14:disconnect()
        end;
    end;
    v_u_10[p_u_12] = {}
    v_u_10[p_u_12].count = 0
    v_u_10[p_u_12].totalWeight = 0
    v_u_10[p_u_12].connections = {}
    local v15 = script:FindFirstChild(p_u_12)
    if v15 ~= nil then
        table.insert(v_u_10[p_u_12].connections, v15.ChildAdded:connect(function(_) --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): f_configureAnimationSet, (copy 2): p_u_12, (copy 3): p_u_13 ]]
            f_configureAnimationSet(p_u_12, p_u_13)
        end))
        table.insert(v_u_10[p_u_12].connections, v15.ChildRemoved:connect(function(_) --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): f_configureAnimationSet, (copy 2): p_u_12, (copy 3): p_u_13 ]]
            f_configureAnimationSet(p_u_12, p_u_13)
        end))
        local v16 = 1
        for _, v17 in pairs(v15:GetChildren()) do
            if v17:IsA("Animation") then
                table.insert(v_u_10[p_u_12].connections, v17.Changed:connect(function(_) --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): f_configureAnimationSet, (copy 2): p_u_12, (copy 3): p_u_13 ]]
                    f_configureAnimationSet(p_u_12, p_u_13)
                end))
                v_u_10[p_u_12][v16] = {}
                v_u_10[p_u_12][v16].anim = v17
                local v18 = v17:FindFirstChild("Weight")
                if v18 == nil then
                    v_u_10[p_u_12][v16].weight = 1
                else
                    v_u_10[p_u_12][v16].weight = v18.Value
                end;
                v_u_10[p_u_12].count = v_u_10[p_u_12].count + 1
                v_u_10[p_u_12].totalWeight = v_u_10[p_u_12].totalWeight + v_u_10[p_u_12][v16].weight
                v16 = v16 + 1
            end;
        end;
    end;
    if v_u_10[p_u_12].count <= 0 then
        for v19, v20 in pairs(p_u_13) do
            v_u_10[p_u_12][v19] = {}
            v_u_10[p_u_12][v19].anim = Instance.new("Animation")
            v_u_10[p_u_12][v19].anim.Name = p_u_12
            v_u_10[p_u_12][v19].anim.AnimationId = v20.id
            v_u_10[p_u_12][v19].weight = v20.weight
            v_u_10[p_u_12].count = v_u_10[p_u_12].count + 1
            v_u_10[p_u_12].totalWeight = v_u_10[p_u_12].totalWeight + v20.weight
        end;
    end;
end;
local function f_scriptChildModified(p21) --[[ Name: scriptChildModified ]] --[[ Line: 148 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): f_configureAnimationSet ]]
    local v22 = v_u_11[p21.Name]
    if v22 ~= nil then
        f_configureAnimationSet(p21.Name, v22)
    end;
end;
script.ChildAdded:connect(f_scriptChildModified)
script.ChildRemoved:connect(f_scriptChildModified)
local v_u_23 = v_u_1
local v_u_24 = "Standing"
local v_u_25 = ""
local v_u_26 = {
    ["wave"] = false,
    ["point"] = false,
    ["dance"] = true,
    ["dance2"] = true,
    ["dance3"] = true,
    ["laugh"] = false,
    ["cheer"] = false
}
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = 1
for v31, v32 in pairs(v_u_11) do
    f_configureAnimationSet(v31, v32)
end;
local v_u_33 = 0
local function _() --[[ Name: stopAllAnimations ]] --[[ Line: 174 ]]
    --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_26, (ref 3): v_u_27, (ref 4): v_u_28, (ref 5): v_u_29 ]]
    local v34 = v_u_25
    local v35 = v_u_26[v34] ~= nil and v_u_26[v34] == false and "idle" or v34
    v_u_25 = ""
    v_u_27 = nil
    if v_u_28 ~= nil then
        v_u_28:disconnect()
    end;
    if v_u_29 ~= nil then
        v_u_29:Stop()
        v_u_29:Destroy()
        v_u_29 = nil
    end;
    return v35;
end;
local function _(p36) --[[ Name: setAnimationSpeed ]] --[[ Line: 196 ]]
    --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_30, (ref 3): v_u_29 ]]
    if v_u_25 ~= "custom_anim" then
        if p36 ~= v_u_30 then
            v_u_30 = p36
            v_u_29:AdjustSpeed(v_u_30)
        end;
    end;
end;
local v_u_37 = nil
local function f_keyFrameReachedFunc(p38) --[[ Name: keyFrameReachedFunc ]] --[[ Line: 209 ]]
    --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_26, (ref 3): v_u_30, (ref 4): v_u_37, (copy 5): v_u_9, (ref 6): v_u_29 ]]
    if p38 == "End" then
        local v39 = v_u_25
        local v40 = v_u_30
        v_u_37(v_u_26[v39] ~= nil and v_u_26[v39] == false and "idle" or v39, 0.15, v_u_9)
        if v_u_25 == "custom_anim" then
            return;
        end;
        if v40 ~= v_u_30 then
            v_u_30 = v40
            v_u_29:AdjustSpeed(v_u_30)
        end;
    end;
end;
local function f_playAnimationInstance(p41, p42, p43, p44) --[[ Name: playAnimationInstance ]] --[[ Line: 224 ]]
    --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (ref 3): v_u_23, (ref 4): v_u_25, (ref 5): v_u_27, (ref 6): v_u_28, (copy 7): f_keyFrameReachedFunc ]]
    if v_u_29 ~= nil then
        v_u_29:Stop(p43)
        v_u_29:Destroy()
    end;
    v_u_30 = 1
    v_u_23 = p41
    local v45 = p44:FindFirstChild("Animator")
    local v46
    if v45 then
        v46 = v45:LoadAnimation(p41)
    else
        v46 = nil
    end;
    v_u_29 = v46
    v_u_29:Play(p43)
    v_u_25 = p42
    v_u_27 = p41
    if v_u_28 ~= nil then
        v_u_28:disconnect()
    end;
    v_u_28 = v_u_29.KeyframeReached:connect(f_keyFrameReachedFunc)
    return v_u_29;
end;
local v_u_47 = false
v_u_37 = function(p48, p49, p50) --[[ Line: 253 ]]
    --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_47, (copy 3): v_u_10, (ref 4): v_u_27, (copy 5): f_playAnimationInstance ]]
    if v_u_25 ~= "custom_anim" or v_u_47 == true then
        if v_u_10[p48] ~= nil then
            local v51 = math.random(1, v_u_10[p48].totalWeight)
            local v52 = 1
            while v_u_10[p48][v52].weight < v51 do
                v51 = v51 - v_u_10[p48][v52].weight
                v52 = v52 + 1
            end;
            local l_anim_0 = v_u_10[p48][v52].anim
            if l_anim_0 ~= v_u_27 then
                f_playAnimationInstance(l_anim_0, p48, p49, p50)
            end;
        end;
    end;
end
local function f_onRunning(p53) --[[ Name: onRunning ]] --[[ Line: 280 ]]
    --[[ Upvalues: (ref 1): v_u_37, (copy 2): v_u_9, (ref 3): v_u_25, (ref 4): v_u_30, (ref 5): v_u_29, (ref 6): v_u_24, (copy 7): v_u_26 ]]
    if p53 > 0.01 then
        v_u_37("walk", 0.1, v_u_9)
        local v54 = p53 / 15
        if v_u_25 ~= "custom_anim" and v54 ~= v_u_30 then
            v_u_30 = v54
            v_u_29:AdjustSpeed(v_u_30)
        end;
        v_u_24 = "Running"
    elseif v_u_26[v_u_25] == nil then
        v_u_37("idle", 0.1, v_u_9)
        v_u_24 = "Standing"
    end;
end;
local function f_onJumping() --[[ Name: onJumping ]] --[[ Line: 298 ]]
    --[[ Upvalues: (ref 1): v_u_37, (copy 2): v_u_9, (ref 3): v_u_33, (ref 4): v_u_24 ]]
    v_u_37("jump", 0.1, v_u_9)
    v_u_33 = 0.31
    v_u_24 = "Jumping"
end;
local function f_onClimbing(p55) --[[ Name: onClimbing ]] --[[ Line: 304 ]]
    --[[ Upvalues: (ref 1): v_u_37, (copy 2): v_u_9, (ref 3): v_u_25, (ref 4): v_u_30, (ref 5): v_u_29, (ref 6): v_u_24 ]]
    v_u_37("climb", 0.1, v_u_9)
    local v56 = p55 / 5
    if v_u_25 ~= "custom_anim" and v56 ~= v_u_30 then
        v_u_30 = v56
        v_u_29:AdjustSpeed(v_u_30)
    end;
    v_u_24 = "Climbing"
end;
local function f_onFreeFall() --[[ Name: onFreeFall ]] --[[ Line: 315 ]]
    --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_37, (copy 3): v_u_9, (ref 4): v_u_24 ]]
    if v_u_33 <= 0 then
        v_u_37("fall", 0.2, v_u_9)
    end;
    v_u_24 = "FreeFall"
end;
local function f_onSwimming(p57) --[[ Name: onSwimming ]] --[[ Line: 334 ]]
    --[[ Upvalues: (ref 1): v_u_37, (copy 2): v_u_9, (ref 3): v_u_25, (ref 4): v_u_30, (ref 5): v_u_29, (ref 6): v_u_24 ]]
    if p57 > 1 then
        v_u_37("swim", 0.4, v_u_9)
        local v58 = p57 / 10
        if v_u_25 ~= "custom_anim" and v58 ~= v_u_30 then
            v_u_30 = v58
            v_u_29:AdjustSpeed(v_u_30)
        end;
        v_u_24 = "Swimming"
    else
        v_u_37("swimidle", 0.4, v_u_9)
        v_u_24 = "Standing"
    end;
end;
local v_u_59 = 0
local function f_move(p60) --[[ Name: move ]] --[[ Line: 348 ]]
    --[[ Upvalues: (ref 1): v_u_59, (ref 2): v_u_33, (ref 3): v_u_24, (ref 4): v_u_37, (copy 5): v_u_9, (ref 6): v_u_25, (copy 7): v_u_26, (ref 8): v_u_27, (ref 9): v_u_28, (ref 10): v_u_29 ]]
    local v61 = p60 - v_u_59
    v_u_59 = p60
    if v_u_33 > 0 then
        v_u_33 = v_u_33 - v61
    end;
    if v_u_24 == "FreeFall" and v_u_33 <= 0 then
        v_u_37("fall", 0.2, v_u_9)
        return;
    elseif v_u_24 == "Seated" then
        v_u_37("sit", 0.5, v_u_9)
        return;
    elseif v_u_24 == "Running" then
        v_u_37("walk", 0.1, v_u_9)
    elseif v_u_24 == "Dead" or (v_u_24 == "GettingUp" or (v_u_24 == "FallingDown" or (v_u_24 == "Seated" or v_u_24 == "PlatformStanding"))) then
        v_u_25 = ""
        v_u_27 = nil
        if v_u_28 ~= nil then
            v_u_28:disconnect()
        end;
        if v_u_29 ~= nil then
            v_u_29:Stop()
            v_u_29:Destroy()
            v_u_29 = nil
        end;
    end;
end;
local v_u_62 = {
    v_u_9.Died:connect(function() --[[ Name: onDied ]] --[[ Line: 294 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = "Dead"
    end),
    v_u_9.Running:connect(f_onRunning),
    v_u_9.Jumping:connect(f_onJumping),
    v_u_9.Climbing:connect(f_onClimbing),
    v_u_9.GettingUp:connect(function() --[[ Name: onGettingUp ]] --[[ Line: 311 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = "GettingUp"
    end),
    v_u_9.FreeFalling:connect(f_onFreeFall),
    v_u_9.FallingDown:connect(function() --[[ Name: onFallingDown ]] --[[ Line: 322 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = "FallingDown"
    end),
    v_u_9.Seated:connect(function() --[[ Name: onSeated ]] --[[ Line: 326 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = "Seated"
    end),
    v_u_9.PlatformStanding:connect(function() --[[ Name: onPlatformStanding ]] --[[ Line: 330 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = "PlatformStanding"
    end),
    v_u_9.Swimming:connect(f_onSwimming)
}
v_u_37("idle", 0.1, v_u_9)
local _ = "Standing"
local v_u_63 = {
    ["control_pressed"] = function(_) --[[ Name: control_pressed ]] --[[ Line: 408 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        v_u_47 = true
    end
}
v_u_63.play_animation_instance = function(_, p_u_64, p_u_65) --[[ Name: play_animation_instance ]] --[[ Line: 396 ]]
    --[[ Upvalues: (ref 1): v_u_47, (copy 2): f_playAnimationInstance, (copy 3): v_u_9 ]]
    v_u_47 = false
    pcall(function() --[[ Line: 398 ]]
        --[[ Upvalues: (ref 1): f_playAnimationInstance, (copy 2): p_u_64, (ref 3): v_u_9, (copy 4): p_u_65 ]]
        local v66 = f_playAnimationInstance(p_u_64, "custom_anim", 0.1, v_u_9)
        if p_u_65 ~= nil then
            v66.TimePosition = p_u_65
        end;
    end)
end;
v_u_63.get_current_animation_instance = function(_) --[[ Name: get_current_animation_instance ]] --[[ Line: 406 ]]
    --[[ Upvalues: (ref 1): v_u_23 ]]
    return v_u_23;
end;
v_u_63.destroy = function(_, _) --[[ Name: destroy ]] --[[ Line: 412 ]]
    --[[ Upvalues: (copy 1): v_u_62, (copy 2): v_u_10 ]]
    for _, v67 in pairs(v_u_62) do
        v67:disconnect()
    end;
    for _, v68 in pairs(v_u_10) do
        for _, v69 in pairs(v68.connections) do
            v69:disconnect()
        end;
    end;
    script:Destroy()
end;
script:WaitForChild("Self").OnInvoke = function() --[[ Name: OnInvoke ]] --[[ Line: 425 ]]
    --[[ Upvalues: (copy 1): v_u_63 ]]
    return v_u_63;
end
while l_Parent_0.Parent ~= nil do
    local _, v70 = wait(0.1)
    f_move(v70)
end;
