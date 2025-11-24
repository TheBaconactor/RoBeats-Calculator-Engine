-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v3 = {}
local v_u_4 = {
    ["Sparkles"] = true,
    ["Sound"] = true,
    ["ParticleEmitter"] = true,
    ["Script"] = true,
    ["LocalScript"] = true,
    ["BodyGyro"] = true,
    ["BodyPosition"] = true,
    ["BodyForce"] = true,
    ["PointLight"] = true,
    ["SpotLight"] = true,
    ["SurfaceLight"] = true,
    ["Fire"] = true
}
local function f_r_itr(p5) --[[ Name: r_itr ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): f_r_itr, (copy 2): v_u_4 ]]
    for _, v6 in pairs(p5:GetChildren()) do
        f_r_itr(v6)
    end;
    if v_u_4[p5.ClassName] == true then
        p5:Destroy()
    end;
end;
v3.sanitize_model = function(_, p_u_7) --[[ Name: sanitize_model ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): f_r_itr, (copy 2): v_u_2, (copy 3): v_u_1 ]]
    if p_u_7 == nil then
        warn("SanitizeCharacter:sanitize_model model is nil")
    else
        local v11, _ = pcall(function() --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): f_r_itr, (copy 2): p_u_7, (ref 3): v_u_2, (ref 4): v_u_1 ]]
            f_r_itr(p_u_7)
            local v8 = p_u_7:FindFirstChild("ForceField")
            if v8 ~= nil then
                v8:Destroy()
            end;
            local v9 = p_u_7:FindFirstChild("Humanoid")
            if v9 ~= nil then
                v9.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
                v9.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
            end;
            if v_u_2.AllowLayeredClothing ~= true then
                for _, v10 in pairs(p_u_7:GetChildren()) do
                    if v10.ClassName == "Accessory" and v_u_1:get_list_of_children_of_classname(v10, "WrapLayer"):count() > 0 then
                        v10:Destroy()
                    end;
                end;
            end;
        end)
        if v11 ~= true then
            warn(v11)
        end;
    end;
end;
return v3;
