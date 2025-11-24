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
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local s_PathfindingService_0 = game:GetService("PathfindingService")
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_14 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_7, (copy 5): v_u_9, (copy 6): v_u_8, (ref 7): v_u_12, (copy 8): v_u_3, (copy 9): s_PathfindingService_0, (copy 10): v_u_4, (copy 11): v_u_5, (copy 12): v_u_11, (ref 13): v_u_13, (ref 14): v_u_14, (copy 15): v_u_10 ]]
        local v15 = v_u_1:new()
        v_u_2:get_base_fn(v15, "get_name")
        v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 33 ]]
            return "No-Scope Arena";
        end;
        v_u_2:get_base_fn(v15, "get_icon")
        v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 35 ]]
            return "rbxassetid://15309921858";
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        v15.load_stage = function(_, p_u_18) --[[ Name: load_stage ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_16, (ref 4): v_u_17 ]]
            v_u_6:singleton():load_model_category(v_u_7.GameStage.NoScopeStage, v_u_7.Category.GameStage, function(p19) --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (copy 3): p_u_18 ]]
                v_u_16 = p19
                v_u_17 = Instance.new("Model", v_u_16)
                p_u_18()
            end)
        end;
        local v_u_20 = v_u_9:new()
        local v_u_21 = v_u_9:new()
        local v_u_22 = v_u_8:new()
        local v_u_23 = 1
        local v_u_24 = v_u_9:new()
        local function _(p_u_25) --[[ Name: spawn_character ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_22, (ref 3): v_u_23, (ref 4): v_u_12, (ref 5): v_u_3, (ref 6): s_PathfindingService_0, (ref 7): v_u_16, (copy 8): v_u_24, (ref 9): v_u_9, (ref 10): v_u_4, (copy 11): v_u_20, (copy 12): v_u_21 ]]
            spawn(function() --[[ Line: 54 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_22, (ref 3): v_u_23, (ref 4): v_u_12, (ref 5): v_u_3, (ref 6): s_PathfindingService_0, (ref 7): v_u_16, (ref 8): v_u_24, (ref 9): v_u_9, (ref 10): v_u_4, (copy 11): p_u_25, (ref 12): v_u_20, (ref 13): v_u_21 ]]
                if v_u_17 == nil then
                    return;
                end;
                local v26
                if v_u_22:count() > 0 then
                    v26 = v_u_22:get(v_u_23):Clone()
                    v_u_23 = v_u_23 + 1
                    if v_u_23 > v_u_22:count() then
                        v_u_23 = 1
                    end;
                else
                    v26 = v_u_12:get_default_character_clone()
                end;
                local v27 = v_u_3:rand_rangei(15, 30)
                local v_u_28 = false
                local function f_humanoid_path_to_destination(p_u_29, p_u_30, p_u_31) --[[ Name: humanoid_path_to_destination ]] --[[ Line: 71 ]]
                    --[[ Upvalues: (ref 1): s_PathfindingService_0, (ref 2): v_u_17 ]]
                    local v_u_32 = s_PathfindingService_0:CreatePath()
                    local v_u_33 = nil
                    local v_u_34 = nil
                    local v_u_35 = nil
                    local v36, _ = pcall(function() --[[ Line: 78 ]]
                        --[[ Upvalues: (copy 1): v_u_32, (copy 2): p_u_29, (copy 3): p_u_30 ]]
                        v_u_32:ComputeAsync(p_u_29.RootPart.Position, p_u_30)
                    end)
                    if v36 and v_u_32.Status == Enum.PathStatus.Success then
                        local v_u_37 = v_u_32:GetWaypoints()
                        local v_u_39 = v_u_32.Blocked:Connect(function(p38) --[[ Line: 84 ]]
                            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_33, (ref 3): v_u_35, (copy 4): p_u_31 ]]
                            if v_u_17 ~= nil then
                                if v_u_33 <= p38 then
                                    v_u_35:Disconnect()
                                    p_u_31()
                                end;
                            end;
                        end)
                        if not v_u_34 then
                            local _ = p_u_29.MoveToFinished:Connect(function(p40) --[[ Line: 93 ]]
                                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_33, (ref 3): v_u_37, (copy 4): p_u_29, (ref 5): v_u_34, (ref 6): v_u_39, (copy 7): p_u_31 ]]
                                if v_u_17 == nil then
                                    return;
                                elseif p40 and v_u_33 < #v_u_37 then
                                    v_u_33 = v_u_33 + 1
                                    local v41 = v_u_37[v_u_33]
                                    if v41.Action == Enum.PathWaypointAction.Jump then
                                        p_u_29.Jump = true
                                    end;
                                    p_u_29:MoveTo(v41.Position)
                                else
                                    v_u_34:Disconnect()
                                    v_u_39:Disconnect()
                                    p_u_31()
                                end;
                            end)
                        end;
                        if #v_u_37 >= 2 then
                            local v42 = 2
                            p_u_29:MoveTo(v_u_37[v42].Position)
                        else
                            p_u_31()
                        end;
                    else
                        p_u_31()
                    end;
                end;
                local v_u_43 = v_u_3:first_child_of_type(v26, "Humanoid")
                v26.Parent = v_u_16
                v_u_24:add_set(v_u_43)
                local l_Animation_0 = Instance.new("Animation")
                l_Animation_0.AnimationId = "rbxassetid://14861286694"
                v_u_3:ptry(function() --[[ Line: 130 ]]
                    --[[ Upvalues: (copy 1): v_u_43, (copy 2): l_Animation_0 ]]
                    v_u_43:LoadAnimation(l_Animation_0):Play()
                end)
                local v_u_44 = v_u_9:new()
                local function f_random_position_away_from_current_slot(p45) --[[ Name: random_position_away_from_current_slot ]] --[[ Line: 134 ]]
                    --[[ Upvalues: (copy 1): v_u_44, (ref 2): v_u_4, (ref 3): p_u_25, (ref 4): v_u_9 ]]
                    v_u_44:clear()
                    local v46 = v_u_4:slot_to_world_position(p_u_25:get_local_game_slot())
                    for v47, v48 in p45:key_itr() do
                        if (v48 - v46).Magnitude > 60 then
                            v_u_44:add(v47, v48)
                        end;
                    end;
                    return v_u_9:random_key_value(v_u_44);
                end;
                local _, v49 = f_random_position_away_from_current_slot(v_u_20)
                v26:SetPrimaryPartCFrame(CFrame.new(v49))
                local function _() --[[ Name: move_to_random_position ]] --[[ Line: 153 ]]
                    --[[ Upvalues: (ref 1): v_u_17, (copy 2): f_random_position_away_from_current_slot, (ref 3): v_u_21, (copy 4): f_humanoid_path_to_destination, (copy 5): v_u_43, (ref 6): v_u_28 ]]
                    if v_u_17 ~= nil then
                        local _, v50 = f_random_position_away_from_current_slot(v_u_21)
                        f_humanoid_path_to_destination(v_u_43, v50, function() --[[ Line: 159 ]]
                            --[[ Upvalues: (ref 1): v_u_28 ]]
                            v_u_28 = true
                        end)
                    end;
                end;
                if v_u_17 ~= nil then
                    local _, v51 = f_random_position_away_from_current_slot(v_u_21)
                    f_humanoid_path_to_destination(v_u_43, v51, function() --[[ Line: 159 ]]
                        --[[ Upvalues: (ref 1): v_u_28 ]]
                        v_u_28 = true
                    end)
                end;
                local v52 = tick()
                wait(0.25)
                local v_u_53 = v_u_28
                local v54 = 0
                local v55 = 0
                local v56 = 0
                while v_u_17 ~= nil and (v_u_43.RootPart ~= nil and v_u_24:contains(v_u_43) == true) do
                    local v57 = tick() - v52
                    v52 = tick()
                    v54 = v54 + v57
                    local l_Velocity_0 = v_u_43.RootPart.Velocity
                    v55 = Vector3.new(l_Velocity_0.X, 0, l_Velocity_0.Z).Magnitude >= 2.5 and 0 or v55 + v57
                    if v55 > 1.25 then
                        v_u_43.Jump = true
                    end;
                    local v58 = false
                    for v59, _ in v_u_24:key_itr() do
                        if v59 ~= v_u_43 and (v59.Health > 0 and (v59.RootPart.Position - v_u_43.RootPart.Position).Magnitude < 20) then
                            v58 = true
                            break;
                        end;
                    end;
                    if (v54 > 5 and v58 == true or v27 < v54) and v_u_43.Health ~= 0 then
                        v_u_43.Health = 0
                        for _, v60 in v_u_3:get_list_of_children_of_classname(v_u_43.RootPart, "ParticleEmitter"):key_itr() do
                            v60.Enabled = true
                        end;
                    end;
                    if v_u_43:GetState() == Enum.HumanoidStateType.Dead then
                        v56 = v56 + v57
                        if v56 > 1 then
                            break;
                        end;
                    elseif v_u_53 and v_u_17 ~= nil then
                        local _, v61 = f_random_position_away_from_current_slot(v_u_21)
                        f_humanoid_path_to_destination(v_u_43, v61, function() --[[ Line: 159 ]]
                            --[[ Upvalues: (ref 1): v_u_53 ]]
                            v_u_53 = true
                        end)
                    end;
                    wait(0.25)
                end;
                v_u_24:remove(v_u_43)
                v26.Parent = nil
            end)
        end;
        local v_u_62 = 9999
        local v_u_63 = nil
        local v_u_64 = nil
        v_u_2:get_base_fn(v15, "setup_stage")
        v15.setup_stage = function(p65, p66) --[[ Name: setup_stage ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_11, (ref 5): v_u_63, (ref 6): v_u_64, (ref 7): v_u_13, (ref 8): v_u_14, (copy 9): v_u_22, (ref 10): v_u_3, (copy 11): v_u_20, (copy 12): v_u_21, (ref 13): v_u_62 ]]
            v_u_16.Parent = v_u_12:get_local_elements_folder()
            local v67 = v_u_12:get_game_sky()
            v67.SkyboxBk = "rbxassetid://6444884337"
            v67.SkyboxDn = "rbxassetid://6444884785"
            v67.SkyboxFt = "rbxassetid://6444884337"
            v67.SkyboxLf = "rbxassetid://6444884337"
            v67.SkyboxRt = "rbxassetid://6444884337"
            v67.SkyboxUp = "rbxassetid://6412503613"
            local v68 = v_u_12:get_game_lighting()
            if p66._player_settings_manager:get_key(v_u_5.Key.BrightnessSettings) == v_u_11.Normal then
                v68.Ambient = Color3.fromRGB(255, 255, 255)
            else
                v68.Ambient = Color3.fromRGB(130, 130, 130)
            end;
            v68.Brightness = 1
            v68.ColorShift_Bottom = Color3.new(0.470588, 0.129412, 0.764706)
            v68.ColorShift_Top = Color3.new(0.14902, 0, 0.647059)
            v68.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v68.ClockTime = 12.5
            v68.GeographicLatitude = 187
            v_u_63 = v_u_16.CenterSection
            p65:on_switch_focus_slot(p66)
            v_u_64 = v_u_13:new(game.ReplicatedStorage.ElementProtos.CharacterShineEffectProto, v_u_14.CHARACTER_POSITION_OFFSET)
            if v_u_16:FindFirstChild("UseNPCProtos") ~= nil then
                v_u_22:clear()
                local l_UseNPCProtos_0 = v_u_16.UseNPCProtos
                l_UseNPCProtos_0.Parent = nil
                for _, v69 in pairs(l_UseNPCProtos_0:GetChildren()) do
                    if v_u_3:first_child_of_type(v69, "Humanoid") ~= nil then
                        v_u_22:push_back(v69)
                    end;
                end;
            end;
            local function _(p70, p71) --[[ Name: add_unique_name_position ]] --[[ Line: 281 ]]
                local l_Name_0 = p71.Name
                while p70:contains(l_Name_0) do
                    l_Name_0 = l_Name_0 .. "*"
                end;
                p70:add(l_Name_0, p71.Position)
            end;
            if v_u_16.Paths:FindFirstChild("SpawnPositions") ~= nil then
                v_u_20:clear()
                local l_SpawnPositions_0 = v_u_16.Paths.SpawnPositions
                l_SpawnPositions_0.Parent = nil
                for _, v72 in pairs(l_SpawnPositions_0:GetChildren()) do
                    if v72:IsA("BasePart") then
                        local v73 = v_u_20
                        local l_Name_1 = v72.Name
                        while v73:contains(l_Name_1) do
                            l_Name_1 = l_Name_1 .. "*"
                        end;
                        v73:add(l_Name_1, v72.Position)
                    elseif v72:IsA("Model") then
                        for _, v74 in pairs(v72:GetChildren()) do
                            local v75 = v_u_20
                            local l_Name_2 = v74.Name
                            while v75:contains(l_Name_2) do
                                l_Name_2 = l_Name_2 .. "*"
                            end;
                            v75:add(l_Name_2, v74.Position)
                        end;
                    end;
                end;
            end;
            if v_u_16.Paths:FindFirstChild("MovePositions") ~= nil then
                v_u_21:clear()
                local l_MovePositions_0 = v_u_16.Paths.MovePositions
                l_MovePositions_0.Parent = nil
                for _, v76 in pairs(l_MovePositions_0:GetChildren()) do
                    if v76:IsA("BasePart") then
                        local v77 = v_u_21
                        local l_Name_3 = v76.Name
                        while v77:contains(l_Name_3) do
                            l_Name_3 = l_Name_3 .. "*"
                        end;
                        v77:add(l_Name_3, v76.Position)
                    elseif v76:IsA("Model") then
                        for _, v78 in pairs(v76:GetChildren()) do
                            local v79 = v_u_21
                            local l_Name_4 = v78.Name
                            while v79:contains(l_Name_4) do
                                l_Name_4 = l_Name_4 .. "*"
                            end;
                            v79:add(l_Name_4, v78.Position)
                        end;
                    end;
                end;
            end;
            v_u_62 = 9999
        end;
        v_u_2:get_base_fn(v15, "on_switch_focus_slot")
        v15.on_switch_focus_slot = function(_, p80) --[[ Name: on_switch_focus_slot ]] --[[ Line: 323 ]]
            --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_4 ]]
            v_u_63:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p80:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v15, "teardown_stage")
        v15.teardown_stage = function(_, p81) --[[ Name: teardown_stage ]] --[[ Line: 331 ]]
            --[[ Upvalues: (ref 1): v_u_64, (copy 2): v_u_24, (ref 3): v_u_16, (ref 4): v_u_17 ]]
            v_u_64:teardown(p81)
            for v82, _ in v_u_24:key_itr() do
                v82.Parent = nil
            end;
            v_u_24:clear()
            v_u_16:Destroy()
            v_u_16 = nil
            v_u_17 = nil
        end;
        v_u_2:get_base_fn(v15, "create_shine_for_slot_at_cframe")
        v15.create_shine_for_slot_at_cframe = function(_, p83, p84, p85) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 345 ]]
            --[[ Upvalues: (ref 1): v_u_64 ]]
            v_u_64:create_shine_for_slot_at_cframe(p83, p84, p85)
        end;
        v_u_2:get_base_fn(v15, "game_update")
        v15.game_update = function(_, p86, p_u_87) --[[ Name: game_update ]] --[[ Line: 350 ]]
            --[[ Upvalues: (ref 1): v_u_64, (ref 2): v_u_62, (ref 3): v_u_10, (copy 4): v_u_24, (ref 5): v_u_17, (copy 6): v_u_22, (ref 7): v_u_23, (ref 8): v_u_12, (ref 9): v_u_3, (ref 10): s_PathfindingService_0, (ref 11): v_u_16, (ref 12): v_u_9, (ref 13): v_u_4, (copy 14): v_u_20, (copy 15): v_u_21 ]]
            v_u_64:update(p86, p_u_87)
            v_u_62 = v_u_62 + v_u_10:TimescaleToDeltaTime(p86)
            if v_u_24:count() < 3 and v_u_62 > 10 then
                v_u_62 = 0
                spawn(function() --[[ Line: 54 ]]
                    --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_22, (ref 3): v_u_23, (ref 4): v_u_12, (ref 5): v_u_3, (ref 6): s_PathfindingService_0, (ref 7): v_u_16, (ref 8): v_u_24, (ref 9): v_u_9, (ref 10): v_u_4, (copy 11): p_u_87, (ref 12): v_u_20, (ref 13): v_u_21 ]]
                    if v_u_17 == nil then
                        return;
                    end;
                    local v88
                    if v_u_22:count() > 0 then
                        v88 = v_u_22:get(v_u_23):Clone()
                        v_u_23 = v_u_23 + 1
                        if v_u_23 > v_u_22:count() then
                            v_u_23 = 1
                        end;
                    else
                        v88 = v_u_12:get_default_character_clone()
                    end;
                    local v89 = v_u_3:rand_rangei(15, 30)
                    local v_u_90 = false
                    local function f_humanoid_path_to_destination(p_u_91, p_u_92, p_u_93) --[[ Name: humanoid_path_to_destination ]] --[[ Line: 71 ]]
                        --[[ Upvalues: (ref 1): s_PathfindingService_0, (ref 2): v_u_17 ]]
                        local v_u_94 = s_PathfindingService_0:CreatePath()
                        local v_u_95 = nil
                        local v_u_96 = nil
                        local v_u_97 = nil
                        local v98, _ = pcall(function() --[[ Line: 78 ]]
                            --[[ Upvalues: (copy 1): v_u_94, (copy 2): p_u_91, (copy 3): p_u_92 ]]
                            v_u_94:ComputeAsync(p_u_91.RootPart.Position, p_u_92)
                        end)
                        if v98 and v_u_94.Status == Enum.PathStatus.Success then
                            local v_u_99 = v_u_94:GetWaypoints()
                            local v_u_101 = v_u_94.Blocked:Connect(function(p100) --[[ Line: 84 ]]
                                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_95, (ref 3): v_u_97, (copy 4): p_u_93 ]]
                                if v_u_17 ~= nil then
                                    if v_u_95 <= p100 then
                                        v_u_97:Disconnect()
                                        p_u_93()
                                    end;
                                end;
                            end)
                            if not v_u_96 then
                                local _ = p_u_91.MoveToFinished:Connect(function(p102) --[[ Line: 93 ]]
                                    --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_95, (ref 3): v_u_99, (copy 4): p_u_91, (ref 5): v_u_96, (ref 6): v_u_101, (copy 7): p_u_93 ]]
                                    if v_u_17 == nil then
                                        return;
                                    elseif p102 and v_u_95 < #v_u_99 then
                                        v_u_95 = v_u_95 + 1
                                        local v103 = v_u_99[v_u_95]
                                        if v103.Action == Enum.PathWaypointAction.Jump then
                                            p_u_91.Jump = true
                                        end;
                                        p_u_91:MoveTo(v103.Position)
                                    else
                                        v_u_96:Disconnect()
                                        v_u_101:Disconnect()
                                        p_u_93()
                                    end;
                                end)
                            end;
                            if #v_u_99 >= 2 then
                                local v104 = 2
                                p_u_91:MoveTo(v_u_99[v104].Position)
                            else
                                p_u_93()
                            end;
                        else
                            p_u_93()
                        end;
                    end;
                    local v_u_105 = v_u_3:first_child_of_type(v88, "Humanoid")
                    v88.Parent = v_u_16
                    v_u_24:add_set(v_u_105)
                    local l_Animation_1 = Instance.new("Animation")
                    l_Animation_1.AnimationId = "rbxassetid://14861286694"
                    v_u_3:ptry(function() --[[ Line: 130 ]]
                        --[[ Upvalues: (copy 1): v_u_105, (copy 2): l_Animation_1 ]]
                        v_u_105:LoadAnimation(l_Animation_1):Play()
                    end)
                    local v_u_106 = v_u_9:new()
                    local function f_random_position_away_from_current_slot(p107) --[[ Name: random_position_away_from_current_slot ]] --[[ Line: 134 ]]
                        --[[ Upvalues: (copy 1): v_u_106, (ref 2): v_u_4, (ref 3): p_u_87, (ref 4): v_u_9 ]]
                        v_u_106:clear()
                        local v108 = v_u_4:slot_to_world_position(p_u_87:get_local_game_slot())
                        for v109, v110 in p107:key_itr() do
                            if (v110 - v108).Magnitude > 60 then
                                v_u_106:add(v109, v110)
                            end;
                        end;
                        return v_u_9:random_key_value(v_u_106);
                    end;
                    local _, v111 = f_random_position_away_from_current_slot(v_u_20)
                    v88:SetPrimaryPartCFrame(CFrame.new(v111))
                    local function _() --[[ Name: move_to_random_position ]] --[[ Line: 153 ]]
                        --[[ Upvalues: (ref 1): v_u_17, (copy 2): f_random_position_away_from_current_slot, (ref 3): v_u_21, (copy 4): f_humanoid_path_to_destination, (copy 5): v_u_105, (ref 6): v_u_90 ]]
                        if v_u_17 ~= nil then
                            local _, v112 = f_random_position_away_from_current_slot(v_u_21)
                            f_humanoid_path_to_destination(v_u_105, v112, function() --[[ Line: 159 ]]
                                --[[ Upvalues: (ref 1): v_u_90 ]]
                                v_u_90 = true
                            end)
                        end;
                    end;
                    if v_u_17 ~= nil then
                        local _, v113 = f_random_position_away_from_current_slot(v_u_21)
                        f_humanoid_path_to_destination(v_u_105, v113, function() --[[ Line: 159 ]]
                            --[[ Upvalues: (ref 1): v_u_90 ]]
                            v_u_90 = true
                        end)
                    end;
                    local v114 = tick()
                    wait(0.25)
                    local v_u_115 = v_u_90
                    local v116 = 0
                    local v117 = 0
                    local v118 = 0
                    while v_u_17 ~= nil and (v_u_105.RootPart ~= nil and v_u_24:contains(v_u_105) == true) do
                        local v119 = tick() - v114
                        v114 = tick()
                        v116 = v116 + v119
                        local l_Velocity_1 = v_u_105.RootPart.Velocity
                        v117 = Vector3.new(l_Velocity_1.X, 0, l_Velocity_1.Z).Magnitude >= 2.5 and 0 or v117 + v119
                        if v117 > 1.25 then
                            v_u_105.Jump = true
                        end;
                        local v120 = false
                        for v121, _ in v_u_24:key_itr() do
                            if v121 ~= v_u_105 and (v121.Health > 0 and (v121.RootPart.Position - v_u_105.RootPart.Position).Magnitude < 20) then
                                v120 = true
                                break;
                            end;
                        end;
                        if (v116 > 5 and v120 == true or v89 < v116) and v_u_105.Health ~= 0 then
                            v_u_105.Health = 0
                            for _, v122 in v_u_3:get_list_of_children_of_classname(v_u_105.RootPart, "ParticleEmitter"):key_itr() do
                                v122.Enabled = true
                            end;
                        end;
                        if v_u_105:GetState() == Enum.HumanoidStateType.Dead then
                            v118 = v118 + v119
                            if v118 > 1 then
                                break;
                            end;
                        elseif v_u_115 and v_u_17 ~= nil then
                            local _, v123 = f_random_position_away_from_current_slot(v_u_21)
                            f_humanoid_path_to_destination(v_u_105, v123, function() --[[ Line: 159 ]]
                                --[[ Upvalues: (ref 1): v_u_115 ]]
                                v_u_115 = true
                            end)
                        end;
                        wait(0.25)
                    end;
                    v_u_24:remove(v_u_105)
                    v88.Parent = nil
                end)
            end;
        end;
        v_u_2:get_base_fn(v15, "should_do_game_start_zoom_in_effect")
        v15.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 361 ]]
            return true, 38.325, 21, 0.75;
        end;
        return v15;
    end
};
