-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

local function _(p1, p2, p3, p4, p5) --[[ Name: CreateNewSound ]] --[[ Line: 10 ]]
    local l_Sound_0 = Instance.new("Sound")
    l_Sound_0.SoundId = p2
    l_Sound_0.Name = p1
    l_Sound_0.archivable = false
    l_Sound_0.Parent = p5
    l_Sound_0.Pitch = p4
    l_Sound_0.Looped = p3
    l_Sound_0.MinDistance = 5
    l_Sound_0.MaxDistance = 150
    l_Sound_0.Volume = 0.65
    return l_Sound_0;
end;
local v_u_6 = script.Parent:FindFirstChild("Head")
if v_u_6 == nil then
    error("Sound script parent has no child Head.")
    return;
else
    local v7 = script.Parent:FindFirstChild("Humanoid")
    if v7 == nil or v7.ClassName ~= "Humanoid" then
        error("Sound script parent has no child Humanoid.")
    else
        local l_Sound_1 = Instance.new("Sound")
        l_Sound_1.SoundId = "rbxasset://sounds/action_get_up.mp3"
        l_Sound_1.Name = "GettingUp"
        l_Sound_1.archivable = false
        l_Sound_1.Parent = v_u_6
        l_Sound_1.Pitch = 1
        l_Sound_1.Looped = false
        l_Sound_1.MinDistance = 5
        l_Sound_1.MaxDistance = 150
        l_Sound_1.Volume = 0.65
        local l_Sound_2 = Instance.new("Sound")
        l_Sound_2.SoundId = "rbxasset://sounds/uuhhh.mp3"
        l_Sound_2.Name = "Died"
        l_Sound_2.archivable = false
        l_Sound_2.Parent = v_u_6
        l_Sound_2.Pitch = 1
        l_Sound_2.Looped = false
        l_Sound_2.MinDistance = 5
        l_Sound_2.MaxDistance = 150
        l_Sound_2.Volume = 0.65
        local l_Sound_3 = Instance.new("Sound")
        l_Sound_3.SoundId = "rbxasset://sounds/action_falling.mp3"
        l_Sound_3.Name = "FreeFalling"
        l_Sound_3.archivable = false
        l_Sound_3.Parent = v_u_6
        l_Sound_3.Pitch = 1
        l_Sound_3.Looped = true
        l_Sound_3.MinDistance = 5
        l_Sound_3.MaxDistance = 150
        l_Sound_3.Volume = 0.65
        local l_Sound_4 = Instance.new("Sound")
        l_Sound_4.SoundId = "rbxasset://sounds/action_jump.mp3"
        l_Sound_4.Name = "Jumping"
        l_Sound_4.archivable = false
        l_Sound_4.Parent = v_u_6
        l_Sound_4.Pitch = 1
        l_Sound_4.Looped = false
        l_Sound_4.MinDistance = 5
        l_Sound_4.MaxDistance = 150
        l_Sound_4.Volume = 0.65
        local l_Sound_5 = Instance.new("Sound")
        l_Sound_5.SoundId = "rbxasset://sounds/action_jump_land.mp3"
        l_Sound_5.Name = "Landing"
        l_Sound_5.archivable = false
        l_Sound_5.Parent = v_u_6
        l_Sound_5.Pitch = 1
        l_Sound_5.Looped = false
        l_Sound_5.MinDistance = 5
        l_Sound_5.MaxDistance = 150
        l_Sound_5.Volume = 0.65
        local l_Sound_6 = Instance.new("Sound")
        l_Sound_6.SoundId = "rbxasset://sounds/impact_water.mp3"
        l_Sound_6.Name = "Splash"
        l_Sound_6.archivable = false
        l_Sound_6.Parent = v_u_6
        l_Sound_6.Pitch = 1
        l_Sound_6.Looped = false
        l_Sound_6.MinDistance = 5
        l_Sound_6.MaxDistance = 150
        l_Sound_6.Volume = 0.65
        local l_Sound_7 = Instance.new("Sound")
        l_Sound_7.SoundId = "rbxasset://sounds/action_footsteps_plastic.mp3"
        l_Sound_7.Name = "Running"
        l_Sound_7.archivable = false
        l_Sound_7.Parent = v_u_6
        l_Sound_7.Pitch = 1.85
        l_Sound_7.Looped = true
        l_Sound_7.MinDistance = 5
        l_Sound_7.MaxDistance = 150
        l_Sound_7.Volume = 0.65
        local l_Sound_8 = Instance.new("Sound")
        l_Sound_8.SoundId = "rbxasset://sounds/action_swim.mp3"
        l_Sound_8.Name = "Swimming"
        l_Sound_8.archivable = false
        l_Sound_8.Parent = v_u_6
        l_Sound_8.Pitch = 1.6
        l_Sound_8.Looped = true
        l_Sound_8.MinDistance = 5
        l_Sound_8.MaxDistance = 150
        l_Sound_8.Volume = 0.65
        local l_Sound_9 = Instance.new("Sound")
        l_Sound_9.SoundId = "rbxasset://sounds/action_footsteps_plastic.mp3"
        l_Sound_9.Name = "Climbing"
        l_Sound_9.archivable = false
        l_Sound_9.Parent = v_u_6
        l_Sound_9.Pitch = 1
        l_Sound_9.Looped = true
        l_Sound_9.MinDistance = 5
        l_Sound_9.MaxDistance = 150
        l_Sound_9.Volume = 0.65
        local v_u_8 = {
            ["Died"] = 0,
            ["Running"] = 1,
            ["Swimming"] = 2,
            ["Climbing"] = 3,
            ["Jumping"] = 4,
            ["GettingUp"] = 5,
            ["FreeFalling"] = 6,
            ["FallingDown"] = 7,
            ["Landing"] = 8,
            ["Splash"] = 9
        }
        local v_u_9 = {
            [v_u_8.Died] = v_u_6:WaitForChild("Died"),
            [v_u_8.Running] = v_u_6:WaitForChild("Running"),
            [v_u_8.Swimming] = v_u_6:WaitForChild("Swimming"),
            [v_u_8.Climbing] = v_u_6:WaitForChild("Climbing"),
            [v_u_8.Jumping] = v_u_6:WaitForChild("Jumping"),
            [v_u_8.GettingUp] = v_u_6:WaitForChild("GettingUp"),
            [v_u_8.FreeFalling] = v_u_6:WaitForChild("FreeFalling"),
            [v_u_8.Landing] = v_u_6:WaitForChild("Landing"),
            [v_u_8.Splash] = v_u_6:WaitForChild("Splash")
        }
        local v_u_25 = {
            ["YForLineGivenXAndTwoPts"] = function(p10, p11, p12, p13, p14) --[[ Name: YForLineGivenXAndTwoPts ]] --[[ Line: 95 ]]
                local v15 = (p12 - p14) / (p11 - p13)
                return v15 * p10 + (p12 - v15 * p11);
            end,
            ["Clamp"] = function(p16, p17, p18) --[[ Name: Clamp ]] --[[ Line: 104 ]]
                return math.min(p18, (math.max(p17, p16)));
            end,
            ["HorizontalSpeed"] = function(p19) --[[ Name: HorizontalSpeed ]] --[[ Line: 109 ]]
                return (p19.Velocity + Vector3.new(0, -p19.Velocity.Y, 0)).magnitude;
            end,
            ["VerticalSpeed"] = function(p20) --[[ Name: VerticalSpeed ]] --[[ Line: 115 ]]
                return math.abs(p20.Velocity.Y);
            end,
            ["Play"] = function(p21) --[[ Name: Play ]] --[[ Line: 121 ]]
                if p21.TimePosition ~= 0 then
                    p21.TimePosition = 0
                end;
                if not p21.IsPlaying then
                    p21.Playing = true
                end;
            end,
            ["Pause"] = function(p22) --[[ Name: Pause ]] --[[ Line: 129 ]]
                if p22.IsPlaying then
                    p22.Playing = false
                end;
            end,
            ["Resume"] = function(p23) --[[ Name: Resume ]] --[[ Line: 134 ]]
                if not p23.IsPlaying then
                    p23.Playing = true
                end;
            end,
            ["Stop"] = function(p24) --[[ Name: Stop ]] --[[ Line: 139 ]]
                if p24.IsPlaying then
                    p24.Playing = false
                end;
                if p24.TimePosition ~= 0 then
                    p24.TimePosition = 0
                end;
            end
        }
        local v_u_26 = {}
        local v_u_27 = nil
        setSoundInPlayingLoopedSounds = function(p28) --[[ Name: setSoundInPlayingLoopedSounds ]] --[[ Line: 159 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            for v29 = 1, #v_u_26 do
                if v_u_26[v29] == p28 then
                    return;
                end;
            end;
            table.insert(v_u_26, p28)
        end;
        stopPlayingLoopedSoundsExcept = function(p30) --[[ Name: stopPlayingLoopedSoundsExcept ]] --[[ Line: 169 ]]
            --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_25 ]]
            for v31 = #v_u_26, 1, -1 do
                if v_u_26[v31] ~= p30 then
                    v_u_25.Pause(v_u_26[v31])
                    table.remove(v_u_26, v31)
                end;
            end;
        end;
        local v_u_32 = {
            [Enum.HumanoidStateType.Dead] = function() --[[ Line: 180 ]]
                --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_25 ]]
                stopPlayingLoopedSoundsExcept()
                v_u_25.Play(v_u_9[v_u_8.Died])
            end,
            [Enum.HumanoidStateType.RunningNoPhysics] = function() --[[ Line: 186 ]]
                stateUpdated(Enum.HumanoidStateType.Running)
            end,
            [Enum.HumanoidStateType.Jumping] = function() --[[ Line: 233 ]]
                --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_9, (copy 3): v_u_8, (ref 4): v_u_25 ]]
                if v_u_27 ~= Enum.HumanoidStateType.Jumping then
                    stopPlayingLoopedSoundsExcept()
                    v_u_25.Play(v_u_9[v_u_8.Jumping])
                end;
            end,
            [Enum.HumanoidStateType.GettingUp] = function() --[[ Line: 242 ]]
                --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_25 ]]
                stopPlayingLoopedSoundsExcept()
                v_u_25.Play(v_u_9[v_u_8.GettingUp])
            end,
            [Enum.HumanoidStateType.Freefall] = function() --[[ Line: 248 ]]
                --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_9, (copy 3): v_u_8 ]]
                if v_u_27 ~= Enum.HumanoidStateType.Freefall then
                    v_u_9[v_u_8.FreeFalling].Volume = 0
                    stopPlayingLoopedSoundsExcept()
                end;
            end,
            [Enum.HumanoidStateType.FallingDown] = function() --[[ Line: 257 ]]
                stopPlayingLoopedSoundsExcept()
            end,
            [Enum.HumanoidStateType.Seated] = function() --[[ Line: 275 ]]
                stopPlayingLoopedSoundsExcept()
            end
        }
        v_u_32[Enum.HumanoidStateType.Running] = function() --[[ Line: 190 ]]
            --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_25, (copy 4): v_u_6 ]]
            local v33 = v_u_9[v_u_8.Running]
            stopPlayingLoopedSoundsExcept(v33)
            if v_u_25.HorizontalSpeed(v_u_6) > 0.5 then
                v_u_25.Resume(v33)
                setSoundInPlayingLoopedSounds(v33)
            else
                stopPlayingLoopedSoundsExcept()
            end;
        end
        v_u_32[Enum.HumanoidStateType.Swimming] = function() --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_25, (copy 3): v_u_6, (copy 4): v_u_9, (copy 5): v_u_8 ]]
            if v_u_27 ~= Enum.HumanoidStateType.Swimming and v_u_25.VerticalSpeed(v_u_6) > 0.1 then
                local v34 = v_u_9[v_u_8.Splash]
                v34.Volume = v_u_25.Clamp(v_u_25.YForLineGivenXAndTwoPts(v_u_25.VerticalSpeed(v_u_6), 100, 0.28, 350, 1), 0, 1)
                v_u_25.Play(v34)
            end;
            local v35 = v_u_9[v_u_8.Swimming]
            stopPlayingLoopedSoundsExcept(v35)
            v_u_25.Resume(v35)
            setSoundInPlayingLoopedSounds(v35)
        end
        v_u_32[Enum.HumanoidStateType.Climbing] = function() --[[ Line: 222 ]]
            --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_25, (copy 4): v_u_6 ]]
            local v36 = v_u_9[v_u_8.Climbing]
            if v_u_25.VerticalSpeed(v_u_6) > 0.1 then
                v_u_25.Resume(v36)
                stopPlayingLoopedSoundsExcept(v36)
            else
                stopPlayingLoopedSoundsExcept()
            end;
            setSoundInPlayingLoopedSounds(v36)
        end
        v_u_32[Enum.HumanoidStateType.Landed] = function() --[[ Line: 261 ]]
            --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_6, (copy 3): v_u_9, (copy 4): v_u_8 ]]
            stopPlayingLoopedSoundsExcept()
            if v_u_25.VerticalSpeed(v_u_6) > 75 then
                local v37 = v_u_9[v_u_8.Landing]
                v37.Volume = v_u_25.Clamp(v_u_25.YForLineGivenXAndTwoPts(v_u_25.VerticalSpeed(v_u_6), 50, 0, 100, 1), 0, 1)
                v_u_25.Play(v37)
            end;
        end
        stateUpdated = function(p38) --[[ Name: stateUpdated ]] --[[ Line: 281 ]]
            --[[ Upvalues: (copy 1): v_u_32, (ref 2): v_u_27 ]]
            if v_u_32[p38] ~= nil then
                v_u_32[p38]()
            end;
            v_u_27 = p38
        end;
        onUpdate = function(p39, p40) --[[ Name: onUpdate ]] --[[ Line: 288 ]]
            --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_27, (copy 4): v_u_6, (ref 5): v_u_25 ]]
            local v41 = p39 / p40
            local v42 = v_u_9[v_u_8.FreeFalling]
            if v_u_27 == Enum.HumanoidStateType.Freefall then
                if v_u_6.Velocity.Y < 0 and v_u_25.VerticalSpeed(v_u_6) > 75 then
                    v_u_25.Resume(v42)
                    v42.Volume = v_u_25.Clamp(v42.Volume + p40 / 1.1 * v41, 0, 1)
                else
                    v42.Volume = 0
                end;
            else
                v_u_25.Pause(v42)
            end;
            local v43 = v_u_9[v_u_8.Running]
            if v_u_27 == Enum.HumanoidStateType.Running and v_u_25.HorizontalSpeed(v_u_6) < 0.5 then
                v_u_25.Pause(v43)
            end;
        end;
        local v_u_44 = 0
        local v_u_46 = {
            v7.Died:connect(function() --[[ Line: 322 ]]
                stateUpdated(Enum.HumanoidStateType.Dead)
            end),
            v7.Running:connect(function() --[[ Line: 323 ]]
                stateUpdated(Enum.HumanoidStateType.Running)
            end),
            v7.Swimming:connect(function() --[[ Line: 324 ]]
                stateUpdated(Enum.HumanoidStateType.Swimming)
            end),
            v7.Climbing:connect(function() --[[ Line: 325 ]]
                stateUpdated(Enum.HumanoidStateType.Climbing)
            end),
            v7.Jumping:connect(function() --[[ Line: 326 ]]
                stateUpdated(Enum.HumanoidStateType.Jumping)
            end),
            v7.GettingUp:connect(function() --[[ Line: 327 ]]
                stateUpdated(Enum.HumanoidStateType.GettingUp)
            end),
            v7.FreeFalling:connect(function() --[[ Line: 328 ]]
                stateUpdated(Enum.HumanoidStateType.Freefall)
            end),
            v7.FallingDown:connect(function() --[[ Line: 329 ]]
                stateUpdated(Enum.HumanoidStateType.FallingDown)
            end),
            v7.StateChanged:connect(function(_, p45) --[[ Line: 331 ]]
                stateUpdated(p45)
            end)
        }
        local function v_u_48(p47) --[[ Line: 336 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            v_u_44 = v_u_44 + p47
            if v_u_44 > 0.25 then
                onUpdate(v_u_44, 0.25)
                v_u_44 = 0
            end;
        end;
        local function v_u_50() --[[ Line: 344 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            for v49 = 1, #v_u_46 do
                v_u_46[v49]:disconnect()
            end;
            v_u_46 = nil
        end;
        local v_u_53 = {
            ["update"] = function(_, p51, p52) --[[ Name: update ]] --[[ Line: 354 ]]
                --[[ Upvalues: (ref 1): v_u_48 ]]
                if v_u_48 then
                    v_u_48(p52.CurveUtil:TimescaleToDeltaTime(p51))
                end;
            end,
            ["destroy"] = function(_, _) --[[ Name: destroy ]] --[[ Line: 360 ]]
                --[[ Upvalues: (ref 1): v_u_50 ]]
                if v_u_50 then
                    v_u_50()
                    v_u_50 = nil
                end;
                script:Destroy()
            end
        }
        script:WaitForChild("Self").OnInvoke = function() --[[ Name: OnInvoke ]] --[[ Line: 369 ]]
            --[[ Upvalues: (copy 1): v_u_53 ]]
            return v_u_53;
        end
    end;
end;
